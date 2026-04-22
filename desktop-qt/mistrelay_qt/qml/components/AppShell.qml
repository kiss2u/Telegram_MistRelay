import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem
import "../pages"

Item {
    anchors.fill: parent

    RowLayout {
        anchors.fill: parent
        anchors.margins: ThemeSystem.Theme.pagePadding
        spacing: 20

        AppSidebar {
            Layout.preferredWidth: 258
            Layout.fillHeight: true
            currentRoute: appViewModel.currentRoute
            onRouteSelected: appViewModel.navigate(route)
            onLogoutRequested: appViewModel.logout()
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 18

            AppHeader {
                Layout.fillWidth: true
                title: appViewModel.windowTitle.replace("MistRelay Desktop Qt · ", "")
                subtitle: "PySide6 + Qt Quick 客户端已接入任务中心、Telegram 网盘、设置与更新链路"
                userName: appViewModel.userDisplayName
                connectionState: appViewModel.connectionState
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: appViewModel.currentRouteIndex

                DashboardPage { }
                DownloadsPage { }
                DrivePage { }
                SettingsPage { }
            }
        }
    }
}
