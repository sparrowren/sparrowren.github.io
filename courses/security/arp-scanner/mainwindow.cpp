#include "mainwindow.h"
#include "ui_mainwindow.h"
#include "arp_scanner.h"
#include "packet_sender.h"
#include <QNetworkInterface>
#include <QMessageBox>
#include <QScrollBar>
#include <QDateTime>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
    , arpScanner(new ArpScanner)

    , packetSender(new PacketSender(arpScanner)) // 传递 arpScanner 实例
{
    ui->setupUi(this);

    // 初始化网络接口列表
    populateInterfaces();

    // 设置线程对象
    arpScanner->moveToThread(&scannerThread);
    packetSender->moveToThread(&senderThread);

    // 启动工作线程
    scannerThread.start();
    senderThread.start();

    // 连接信号槽
    connect(arpScanner, &ArpScanner::hostFound,  // 连接 hostFound 信号
            this, &MainWindow::updateTable);     // 到 updateTable 槽
    connect(arpScanner, &ArpScanner::log,
            this, &MainWindow::logMessage);
    connect(packetSender, &PacketSender::log,
            this, &MainWindow::logMessage);

    // 设置默认值
    ui->networkEdit->setText("192.168.24.35/24");
    ui->spoofMacEdit->setInputMask("HH:HH:HH:HH:HH:HH;_");
    ui->stopAttackButton->setEnabled(true); // 初始启用停止攻击按钮
    ui->stopScanButton->setEnabled(false);  // 初始禁用停止扫描按钮
    // 初始化主机列表
    ui->hostTable->setColumnCount(2);
    ui->hostTable->setHorizontalHeaderLabels({"IP Address", "MAC Address"});
}


MainWindow::~MainWindow()
{
    // 停止并等待线程结束
    scannerThread.quit();
    senderThread.quit();
    scannerThread.wait();
    senderThread.wait();

    delete ui;
    delete arpScanner;
    delete packetSender;
}

void MainWindow::populateInterfaces()
{
    ui->interfaceCombo->clear();
    foreach (const QNetworkInterface &interface, QNetworkInterface::allInterfaces()) {
        // 过滤无效接口
        if (interface.flags().testFlag(QNetworkInterface::IsUp) &&
            !interface.flags().testFlag(QNetworkInterface::IsLoopBack)) {
            // 获取接口的IP地址
            foreach (const QNetworkAddressEntry &entry, interface.addressEntries()) {
                if (entry.ip().protocol() == QAbstractSocket::IPv4Protocol) {
                    QString displayName = QString("%1 (%2)")
                    .arg(interface.humanReadableName())
                        .arg(entry.ip().toString());
                    ui->interfaceCombo->addItem(displayName, interface.name());
                    break;
                }
            }
        }
    }
}


void MainWindow::on_scanButton_clicked()
{
    if (!validateScanInputs()) return;
    ui->scanButton->setEnabled(false);
    ui->stopScanButton->setEnabled(true); // 启用停止扫描按钮
    // 获取扫描参数
    QString network = getSelectedNetwork();
    QString interface = ui->interfaceCombo->currentData().toString();

    // 确保接口有效
    if (interface.isEmpty()) {
        showError("No valid network interface selected.");
        return;
    }

    // 禁用扫描按钮防止重复点击
    //ui->scanButton->setEnabled(false);

    // 发起异步扫描
    QMetaObject::invokeMethod(arpScanner, "startScan",
                              Qt::QueuedConnection,
                              Q_ARG(QString, network),
                              Q_ARG(QString, interface));
}
void MainWindow::on_stopScanButton_clicked() {
    arpScanner->stopScan();
    ui->scanButton->setEnabled(true);
    ui->stopScanButton->setEnabled(false);
}
void MainWindow::updateTable(const QString &ip, const QString &mac)
{
    // 检查是否已存在该IP地址
    for (int row = 0; row < ui->hostTable->rowCount(); ++row) {
        if (ui->hostTable->item(row, 0)->text() == ip) {
            return;  // 如果已存在，则跳过
        }
    }

    // 添加新行
    int row = ui->hostTable->rowCount();
    ui->hostTable->insertRow(row);

    // 显示IP地址
    QTableWidgetItem *ipItem = new QTableWidgetItem(ip);
    ui->hostTable->setItem(row, 0, ipItem);

    // 显示MAC地址
    QTableWidgetItem *macItem = new QTableWidgetItem(mac);
    ui->hostTable->setItem(row, 1, macItem);
}


// 启动攻击按钮点击处理
void MainWindow::on_startAttackButton_clicked()
{
    if (!validateAttackInputs()) return;  // 使用新的验证函数

    // 获取攻击参数
    ui->startAttackButton->setEnabled(false);
    ui->stopAttackButton->setEnabled(true);

    QString interface = ui->interfaceCombo->currentData().toString();
    QString targetIp = ui->targetIpEdit->text();
    QString spoofIp = ui->spoofIpEdit->text();
    QString spoofMac = ui->spoofMacEdit->text();
    bool isBroadcast = ui->broadcastRadio->isChecked();

    // 启动攻击线程
    QString targetMac = ui->targetMacEdit->text().trimmed();

    QMetaObject::invokeMethod(packetSender, "startAttack",
                              Qt::QueuedConnection,
                              Q_ARG(QString, interface),
                              Q_ARG(QString, targetIp),
                              Q_ARG(QString, targetMac),  // 新增参数
                              Q_ARG(QString, spoofIp),
                              Q_ARG(QString, spoofMac),
                              Q_ARG(bool, isBroadcast));
    logMessage(QString("[Info] Attack started on %1").arg(interface));
}

void MainWindow::on_clearLogsButton_clicked()
{
    // 实现清除日志的逻辑
    ui->logText->clear();  // 假设 logTextEdit 是日志显示的 QTextEdit
}
QString MainWindow::getSelectedNetwork()
{
    QString network = ui->networkEdit->text().trimmed();
    if (network.isEmpty()) {
        showError("Network address cannot be empty.");
        return QString();
    }
    return network;
}

// 停止攻击按钮点击处理
void MainWindow::on_stopAttackButton_clicked()
{
    QMetaObject::invokeMethod(packetSender, "stopAttack", Qt::QueuedConnection);
    ui->startAttackButton->setEnabled(true);
    ui->stopAttackButton->setEnabled(false);
}

bool MainWindow::validateScanInputs()
{
    // 1. 网络接口验证
    if (ui->interfaceCombo->currentIndex() == -1) {
        showError("Please select a valid network interface.");
        return false;
    }

    // 2. 网络地址格式验证
    QRegularExpression networkRegex(
        "^(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第一段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第二段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第三段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"     // 第四段 (0-255)
        "(\\/([0-9]|[1-2][0-9]|3[0-2]))?$"                // 子网掩码 (可选)
        );

    QString network = ui->networkEdit->text().trimmed();
    if (network.isEmpty()) {
        showError("Network address cannot be empty.");
        return false;
    }
    if (!networkRegex.match(network).hasMatch()) {
        showError("Invalid network address. Please enter a valid network (e.g., 192.168.1.0/24).");
        return false;
    }

    return true;
}

bool MainWindow::validateAttackInputs()
{
    // 1. 网络接口验证
    if (ui->interfaceCombo->currentIndex() == -1) {
        showError("Please select a valid network interface.");
        return false;
    }

    // 2. IP地址格式验证
    QRegularExpression ipRegex(
        "^(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第一段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第二段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\\."  // 第三段 (0-255)
        "(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])$"    // 第四段 (0-255)
        );

    // 验证目标IP地址
    QString targetIp = ui->targetIpEdit->text().trimmed();
    if (targetIp.isEmpty()) {
        showError("Target IP address cannot be empty.");
        return false;
    }
    if (!ipRegex.match(targetIp).hasMatch()) {
        showError("Invalid target IP address. Please enter a valid IP (e.g., 192.168.1.100).");
        return false;
    }
    // 在 validateAttackInputs() 中添加目标MAC验证
    QString targetMac = ui->targetMacEdit->text().trimmed(); // 新增加的输入框
    if (!isBroadcast && targetMac.isEmpty()) {
        showError("Target MAC address cannot be empty in unicast mode.");
        return false;
    }

    // 验证伪造IP地址
    QString spoofIp = ui->spoofIpEdit->text().trimmed();
    if (spoofIp.isEmpty()) {
        showError("Spoof IP address cannot be empty.");
        return false;
    }
    if (!ipRegex.match(spoofIp).hasMatch()) {
        showError("Invalid spoof IP address. Please enter a valid IP (e.g., 192.168.1.1).");
        return false;
    }

    // 3. MAC地址格式验证
    QRegularExpression macRegex(
        "^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"  // MAC地址格式 (00:11:22:33:44:55 或 00-11-22-33-44-55)
        );
    QString spoofMac = ui->spoofMacEdit->text().trimmed();
    if (spoofMac.isEmpty()) {
        showError("Spoof MAC address cannot be empty.");
        return false;
    }
    if (!macRegex.match(spoofMac).hasMatch()) {
        showError("Invalid MAC address. Please enter a valid MAC (e.g., 00:11:22:33:44:55).");
        return false;
    }

    return true;
}



// 显示错误对话框
void MainWindow::showError(const QString &message)
{
    QMessageBox::critical(this, "Input Error", message);
    logMessage("[Error] " + message);
}

// 日志记录
void MainWindow::logMessage(const QString &message)
{
    QString timestamp = QDateTime::currentDateTime().toString("[yyyy-MM-dd hh:mm:ss]");
    ui->logText->append(timestamp + " " + message);

    // 自动滚动到底部
    QScrollBar *scrollbar = ui->logText->verticalScrollBar();
    scrollbar->setValue(scrollbar->maximum());
}

// 双击主机列表项处理
void MainWindow::on_hostTable_itemDoubleClicked(QTableWidgetItem *item) {
    int row = item->row();
    QString ip = ui->hostTable->item(row, 0)->text();
    QString mac = ui->hostTable->item(row, 1)->text();
    ui->targetIpEdit->setText(ip);
    ui->targetMacEdit->setText(mac); // 新增目标MAC输入框
}

