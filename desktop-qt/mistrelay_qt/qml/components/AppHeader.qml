import QtQuick
import QtQuick.Layouts
import "../theme" as ThemeSystem

GlassCard {
    id: root

    property string title: ""
    property string subtitle: ""
    property string userName: ""
    property string connectionState: "disconnected"

    backgroundColor: "#f8fbffd6"
    borderColor: "#bde8f5ff"
    height: 110

    RowLayout {
        anchors.fill: parent
        spacing: 20

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                text: root.title
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 28
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                text: root.subtitle
                color: ThemeSystem.Theme.textSecondary
                font.pixelSize: 14
                font.family: ThemeSystem.Theme.fontFamily
            }
        }

        Rectangle {
            radius: 999
            color: root.connectionState === "connected"
                   ? ThemeSystem.Theme.successSoft
                   : root.connectionState === "connecting"
                     ? ThemeSystem.Theme.warningSoft
                     : ThemeSystem.Theme.dangerSoft
            border.width: 1
            border.color: root.connectionState === "connected"
                          ? "#86efac"
                          : root.connectionState === "connecting"
                            ? "#fcd34d"
                            : "#fca5a5"
            Layout.preferredHeight: 40
            Layout.preferredWidth: 140

            Text {
                anchors.centerIn: parent
                text: root.connectionState === "connected"
                      ? "状态流在线"
                      : root.connectionState === "connecting"
                        ? "正在连接"
                        : "状态流离线"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 13
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }
        }

        Rectangle {
            radius: ThemeSystem.Theme.radiusMedium
            color: "#ffffff"
            border.width: 1
            border.color: ThemeSystem.Theme.lineColor
            Layout.preferredWidth: 168
            Layout.preferredHeight: 52

            RowLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Rectangle {
                    Layout.preferredHeight: 32
                    Layout.preferredWidth: 32
                    radius: 16
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: ThemeSystem.Theme.colorPrimary }
                        GradientStop { position: 1.0; color: "#764ba2" }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: root.userName.length > 0 ? root.userName[0].toUpperCase() : "M"
                        color: "#ffffff"
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: root.userName || "未登录"
                        color: ThemeSystem.Theme.textPrimary
                        font.bold: true
                        font.pixelSize: 14
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "Qt Beta"
                        color: ThemeSystem.Theme.textTertiary
                        font.pixelSize: 12
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }
            }
        }
    }
}
