#include "arp_scanner.h"
#include <netinet/ether.h>
#include <arpa/inet.h>
#include <QNetworkInterface>
#include <QtConcurrent/QtConcurrent>

ArpScanner::ArpScanner(QObject *parent) : QObject(parent), handle(nullptr), isRunning(false) {}

void ArpScanner::startScan(const QString &network, const QString &interface)
{
    char errbuf[PCAP_ERRBUF_SIZE];
    isRunning = true;

    // 打开网络接口
    handle = pcap_open_live(interface.toUtf8().constData(), BUFSIZ, 1, 1000, errbuf);
    if (!handle) {
        emit log("[Error] Failed to open interface: " + QString(errbuf));
        return;
    }

    // 解析网络范围
    QStringList parts = network.split('/');
    struct in_addr baseIp;
    inet_pton(AF_INET, parts[0].toUtf8().constData(), &baseIp);
    int maskBits = parts[1].toInt();

    // 计算扫描范围
    uint32_t networkAddress = ntohl(baseIp.s_addr) & (~((1 << (32 - maskBits)) - 1));
    uint32_t broadcastAddress = networkAddress | ((1 << (32 - maskBits)) - 1);

    // 发送ARP请求（在子线程中执行）
    QtConcurrent::run([=]() {
        for (uint32_t ip = networkAddress + 1; ip < broadcastAddress && isRunning; ++ip) {
            struct in_addr targetIp;
            targetIp.s_addr = htonl(ip);
            sendArpRequest(handle, interface, QString(inet_ntoa(targetIp)));
        }
    });

    // 捕获响应（异步回调）
    pcap_loop(handle, 0, packetHandler, reinterpret_cast<u_char*>(this));
}

void ArpScanner::stopScan() {
    isRunning = false;
    if (handle) {
        pcap_breakloop(handle);  // 关键：中断抓包循环
        pcap_close(handle);
        handle = nullptr;
    }
    emit log("[Info] Scan stopped");
}

// 静态包处理函数
void ArpScanner::packetHandler(u_char *userData, const pcap_pkthdr *header, const u_char *packet) {
    ArpScanner *scanner = reinterpret_cast<ArpScanner*>(userData);
    struct ether_arp *arp = (struct ether_arp*)(packet + sizeof(struct ether_header));

    QString srcIp = QString("%1.%2.%3.%4")
                        .arg(arp->arp_spa[0])
                        .arg(arp->arp_spa[1])
                        .arg(arp->arp_spa[2])
                        .arg(arp->arp_spa[3]);

    QString srcMac = QString("%1:%2:%3:%4:%5:%6")
                         .arg(arp->arp_sha[0], 2, 16, QLatin1Char('0'))
                         .arg(arp->arp_sha[1], 2, 16, QLatin1Char('0'))
                         .arg(arp->arp_sha[2], 2, 16, QLatin1Char('0'))
                         .arg(arp->arp_sha[3], 2, 16, QLatin1Char('0'))
                         .arg(arp->arp_sha[4], 2, 16, QLatin1Char('0'))
                         .arg(arp->arp_sha[5], 2, 16, QLatin1Char('0'));

    // 添加到缓存列表（避免重复）
    bool exists = false;
    for (const auto &host : scanner->activeHosts) {
        if (host.first == srcIp) {
            exists = true;
            break;
        }
    }
    if (!exists) {
        scanner->activeHosts.append(qMakePair(srcIp, srcMac));
    }

    emit scanner->hostFound(srcIp, srcMac);
}

QString ArpScanner::getTargetMacFromCache(const QString &targetIp) {
    for (const auto &host : activeHosts) {
        if (host.first == targetIp) {
            return host.second;
        }
    }
    return QString(); // 未找到返回空字符串
}

void ArpScanner::sendArpRequest(pcap_t *handle, const QString &interface, const QString &targetIp)
{
    u_char packet[42]; // ARP包大小

    // 以太网帧头
    struct ether_header *eth = (struct ether_header *)packet;
    memset(eth->ether_dhost, 0xFF, ETHER_ADDR_LEN); // 广播地址

    // 获取本机MAC地址
    QNetworkInterface iface = QNetworkInterface::interfaceFromName(interface);
    if (!iface.isValid()) {
        emit log("[Error] Invalid network interface: " + interface);
        return;
    }
    QString localMac = iface.hardwareAddress();
    sscanf(localMac.toUtf8().constData(), "%hhx:%hhx:%hhx:%hhx:%hhx:%hhx",
           &eth->ether_shost[0], &eth->ether_shost[1],
           &eth->ether_shost[2], &eth->ether_shost[3],
           &eth->ether_shost[4], &eth->ether_shost[5]);
    eth->ether_type = htons(ETHERTYPE_ARP);

    // ARP数据部分
    struct ether_arp *arp = (struct ether_arp *)(packet + sizeof(ether_header));
    arp->ea_hdr.ar_hrd = htons(ARPHRD_ETHER); // 硬件类型：以太网
    arp->ea_hdr.ar_pro = htons(ETHERTYPE_IP); // 协议类型：IPv4
    arp->ea_hdr.ar_hln = ETHER_ADDR_LEN;      // MAC地址长度
    arp->ea_hdr.ar_pln = 4;                   // IP地址长度
    arp->ea_hdr.ar_op = htons(ARPOP_REQUEST); // ARP请求类型

    // 发送方MAC地址
    memcpy(arp->arp_sha, eth->ether_shost, ETHER_ADDR_LEN);

    // 发送方IP地址
    QString localIp = iface.addressEntries().first().ip().toString();
    struct in_addr localIpAddr;
    inet_pton(AF_INET, localIp.toUtf8().constData(), &localIpAddr);
    memcpy(arp->arp_spa, &localIpAddr.s_addr, sizeof(uint32_t));

    // 目标MAC地址（未知）
    memset(arp->arp_tha, 0x00, ETHER_ADDR_LEN);

    // 目标IP地址
    struct in_addr targetIpAddr;
    inet_pton(AF_INET, targetIp.toUtf8().constData(), &targetIpAddr);
    memcpy(arp->arp_tpa, &targetIpAddr.s_addr, sizeof(uint32_t));

    // 发送ARP请求包
    if (pcap_sendpacket(handle, packet, sizeof(packet)) != 0) {
        emit log("[Error] Failed to send ARP request: " + QString(pcap_geterr(handle)));
    }
}

