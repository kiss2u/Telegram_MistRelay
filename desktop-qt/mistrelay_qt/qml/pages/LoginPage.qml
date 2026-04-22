import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem
import "../components"

Item {
    anchors.fill: parent

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#eef4ff" }
            GradientStop { position: 1.0; color: "#f8fafc" }
        }
    }

    Rectangle {
        x: width * 0.08
        y: height * 0.15
        width: 280
        height: 280
        radius: 140
        color: "#42667eea"
    }

    Rectangle {
        x: width * 0.72
        y: height * 0.62
        width: 220
        height: 220
        radius: 110
        color: "#2a764ba2"
    }

    GlassCard {
        anchors.centerIn: parent
        width: 480
        height: 560
        backgroundColor: "#ecffffff"

        ColumnLayout {
            anchors.fill: parent
            spacing: 18

            Text {
                text: "MistRelay Desktop"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 32
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                text: "PySide6 + Qt Quick（QML）Windows Beta。已接入会话恢复、任务中心、网盘、设置和独立更新通道。"
                color: ThemeSystem.Theme.textSecondary
                font.pixelSize: 14
                wrapMode: Text.WordWrap
                font.family: ThemeSystem.Theme.fontFamily
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 1
                color: ThemeSystem.Theme.lineColor
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "服务端地址"
                    color: ThemeSystem.Theme.textPrimary
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                AppTextField {
                    Layout.fillWidth: true
                    text: loginViewModel.serverBaseUrl
                    placeholderText: "例如 http://127.0.0.1:8000"
                    onTextEdited: loginViewModel.setServerBaseUrl(text)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "用户名"
                    color: ThemeSystem.Theme.textPrimary
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                AppTextField {
                    Layout.fillWidth: true
                    text: loginViewModel.username
                    placeholderText: "请输入账号"
                    onTextEdited: loginViewModel.setUsername(text)
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    text: "密码"
                    color: ThemeSystem.Theme.textPrimary
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                AppTextField {
                    Layout.fillWidth: true
                    text: loginViewModel.password
                    echoMode: TextInput.Password
                    placeholderText: "请输入密码"
                    onTextEdited: loginViewModel.setPassword(text)
                }
            }

            Rectangle {
                visible: loginViewModel.errorMessage.length > 0
                Layout.fillWidth: true
                radius: ThemeSystem.Theme.radiusMedium
                color: ThemeSystem.Theme.dangerSoft
                border.width: 1
                border.color: "#fca5a5"
                implicitHeight: errorText.implicitHeight + 22

                Text {
                    id: errorText
                    anchors.fill: parent
                    anchors.margins: 12
                    text: loginViewModel.errorMessage
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 13
                    font.family: ThemeSystem.Theme.fontFamily
                }
            }

            Rectangle {
                visible: loginViewModel.infoMessage.length > 0
                Layout.fillWidth: true
                radius: ThemeSystem.Theme.radiusMedium
                color: ThemeSystem.Theme.infoSoft
                border.width: 1
                border.color: "#93c5fd"
                implicitHeight: infoText.implicitHeight + 22

                Text {
                    id: infoText
                    anchors.fill: parent
                    anchors.margins: 12
                    text: loginViewModel.infoMessage
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 13
                    font.family: ThemeSystem.Theme.fontFamily
                }
            }

            Item {
                Layout.fillHeight: true
            }

            PrimaryButton {
                Layout.fillWidth: true
                text: loginViewModel.busy ? "正在登录..." : "进入客户端"
                enabled: !loginViewModel.busy
                onClicked: loginViewModel.submitLogin()
            }
        }
    }
}
