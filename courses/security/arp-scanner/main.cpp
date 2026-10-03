#include "mainwindow.h"
#include <QApplication>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);

    // 设置应用程序信息
    app.setApplicationName("ARP Spoofer");
    app.setApplicationVersion("1.0");
    app.setOrganizationName("Network Security Lab");

    MainWindow mainWindow;
    mainWindow.show();

    return app.exec();
}
