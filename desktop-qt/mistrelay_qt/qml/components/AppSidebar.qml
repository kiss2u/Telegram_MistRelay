import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem

Rectangle {
    id: root

    signal routeSelected(string route)
    signal logoutRequested()

    property string currentRoute: "dashboard"

    gradient: Gradient {
        orientation: Gradient.Vertical
        GradientStop { position: 0.0; color: ThemeSystem.Theme.sidebarStart }
        GradientStop { position: 1.0; color: ThemeSystem.Theme.sidebarEnd }
    }
    radius: 30

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22
        spacing: 18

        ColumnLayout {
            spacing: 6

            Text {
                text: "MistRelay"
                color: "#ffffff"
                font.pixelSize: 28
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                text: "Desktop Qt Beta"
                color: "#cbd5e1"
                font.pixelSize: 13
                font.family: ThemeSystem.Theme.fontFamily
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: "#20ffffff"
        }

        SidebarButton {
            Layout.fillWidth: true
            text: "概览"
            glyph: "◉"
            active: root.currentRoute === "dashboard"
            onClicked: root.routeSelected("dashboard")
        }

        SidebarButton {
            Layout.fillWidth: true
            text: "任务中心"
            glyph: "▣"
            active: root.currentRoute === "downloads"
            onClicked: root.routeSelected("downloads")
        }

        SidebarButton {
            Layout.fillWidth: true
            text: "网盘"
            glyph: "◆"
            active: root.currentRoute === "drive"
            onClicked: root.routeSelected("drive")
        }

        SidebarButton {
            Layout.fillWidth: true
            text: "设置"
            glyph: "⚙"
            active: root.currentRoute === "settings"
            onClicked: root.routeSelected("settings")
        }

        Item {
            Layout.fillHeight: true
        }

        SidebarButton {
            Layout.fillWidth: true
            text: "退出登录"
            glyph: "↩"
            active: false
            onClicked: root.logoutRequested()
        }
    }
}
