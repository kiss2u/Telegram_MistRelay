import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem
import "../components"

Item {
    id: root

    anchors.fill: parent

    readonly property bool compactLayout: width < 1320 || height < 860
    readonly property real pagePadding: Math.max(28, Math.min(64, width * 0.05))
    readonly property real contentMaxWidth: compactLayout ? 760 : 1160
    readonly property real heroWidth: compactLayout ? contentMaxWidth : Math.max(460, Math.min(600, contentMaxWidth * 0.56))
    readonly property real formWidth: compactLayout ? contentMaxWidth : Math.max(400, Math.min(460, contentMaxWidth * 0.38))

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#edf6ff" }
            GradientStop { position: 0.55; color: "#f7fbff" }
            GradientStop { position: 1.0; color: "#f8fafc" }
        }
    }

    Rectangle {
        x: width * 0.05
        y: -height * 0.04
        width: 420
        height: 420
        radius: width / 2
        color: "#9ed8ff"
        opacity: 0.38
    }

    Rectangle {
        x: width * 0.72
        y: height * 0.54
        width: 340
        height: 340
        radius: width / 2
        color: "#9ce6cb"
        opacity: 0.28
    }

    Item {
        anchors.fill: parent
        anchors.margins: root.pagePadding

        Flickable {
            id: viewport
            anchors.fill: parent
            contentWidth: width
            contentHeight: Math.max(height, contentShell.implicitHeight + root.pagePadding * 2)
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Item {
                width: viewport.width
                height: viewport.contentHeight

                Item {
                    id: contentShell
                    width: Math.min(root.contentMaxWidth, parent.width)
                    implicitHeight: layout.implicitHeight
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: Math.max(0, (parent.height - implicitHeight) / 2)

                    ColumnLayout {
                        id: layout
                        width: parent.width
                        spacing: 18

                        GridLayout {
                            width: parent.width
                            columns: root.compactLayout ? 1 : 2
                            columnSpacing: 28
                            rowSpacing: 24

                            GlassCard {
                                id: heroCard
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                Layout.preferredWidth: root.heroWidth
                                implicitHeight: heroContent.implicitHeight + padding * 2
                                backgroundColor: "#dc0f172a"
                                borderColor: "#24ffffff"

                                ColumnLayout {
                                    id: heroContent
                                    anchors.fill: parent
                                    spacing: 24

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Rectangle {
                                            radius: 999
                                            color: "#1d4ed8"
                                            Layout.preferredHeight: 32
                                            Layout.preferredWidth: 108

                                            Text {
                                                anchors.centerIn: parent
                                                text: "Desktop Qt"
                                                color: "#ffffff"
                                                font.pixelSize: 12
                                                font.bold: true
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }
                                        }

                                        Rectangle {
                                            radius: 999
                                            color: "#0f766e"
                                            Layout.preferredHeight: 32
                                            Layout.preferredWidth: 96

                                            Text {
                                                anchors.centerIn: parent
                                                text: "Beta 通道"
                                                color: "#ecfeff"
                                                font.pixelSize: 12
                                                font.bold: true
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }
                                        }

                                        Item {
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            text: "会话恢复已启用"
                                            color: "#dbeafe"
                                            font.pixelSize: 12
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        Text {
                                            text: "更稳的桌面入口，先把连接握稳。"
                                            color: "#ffffff"
                                            font.pixelSize: root.compactLayout ? 32 : 42
                                            font.bold: true
                                            wrapMode: Text.WordWrap
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }

                                        Text {
                                            text: "登录页现在按桌面窗口重新布局，左侧保留产品上下文，右侧集中处理服务端连接、账号登录和状态反馈，不再靠固定尺寸硬撑。"
                                            color: "#dbe7f4"
                                            font.pixelSize: 15
                                            wrapMode: Text.WordWrap
                                            lineHeight: 1.25
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }
                                    }

                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: root.compactLayout ? 1 : 2
                                        rowSpacing: 12
                                        columnSpacing: 12

                                        Repeater {
                                            model: [
                                                {
                                                    "title": "任务中心",
                                                    "body": "下载队列、失败重试和本地缓存都已经接入。"
                                                },
                                                {
                                                    "title": "网盘浏览",
                                                    "body": "目录、缩略图和文件操作在一个桌面流里处理。"
                                                },
                                                {
                                                    "title": "独立更新",
                                                    "body": "Qt Beta 客户端通过单独通道拉取清单和安装包。"
                                                },
                                                {
                                                    "title": "代理支持",
                                                    "body": "客户端支持 HTTP 和 SOCKS5 代理，适合内网或转发场景。"
                                                }
                                            ]

                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                radius: ThemeSystem.Theme.radiusMedium
                                                color: "#12ffffff"
                                                border.width: 1
                                                border.color: "#22ffffff"
                                                implicitHeight: featureBody.implicitHeight + 46

                                                Column {
                                                    anchors.fill: parent
                                                    anchors.margins: 16
                                                    spacing: 8

                                                    Text {
                                                        text: modelData.title
                                                        color: "#ffffff"
                                                        font.pixelSize: 15
                                                        font.bold: true
                                                        font.family: ThemeSystem.Theme.fontFamily
                                                    }

                                                    Text {
                                                        id: featureBody
                                                        width: parent.width
                                                        text: modelData.body
                                                        color: "#d6e5f3"
                                                        font.pixelSize: 13
                                                        wrapMode: Text.WordWrap
                                                        lineHeight: 1.25
                                                        font.family: ThemeSystem.Theme.fontFamily
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        radius: ThemeSystem.Theme.radiusLarge
                                        color: "#12ffffff"
                                        border.width: 1
                                        border.color: "#2effffff"
                                        implicitHeight: statusColumn.implicitHeight + 32

                                        ColumnLayout {
                                            id: statusColumn
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            spacing: 8

                                            Text {
                                                text: loginViewModel.busy ? "正在连接服务端" : "准备连接"
                                                color: "#ffffff"
                                                font.pixelSize: 16
                                                font.bold: true
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }

                                            Text {
                                                text: loginViewModel.busy
                                                      ? "客户端正在提交账号信息并等待服务端响应。"
                                                      : "输入服务端地址、用户名和密码后即可进入客户端。"
                                                color: "#d6e5f3"
                                                font.pixelSize: 13
                                                wrapMode: Text.WordWrap
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }
                                        }
                                    }
                                }
                            }

                            GlassCard {
                                id: formCard
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                Layout.preferredWidth: root.formWidth
                                implicitHeight: formContent.implicitHeight + padding * 2
                                backgroundColor: "#f7fbffef"
                                borderColor: "#b7dbf6"

                                ColumnLayout {
                                    id: formContent
                                    anchors.fill: parent
                                    spacing: 18

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 8

                                        Text {
                                            text: "登录到 MistRelay"
                                            color: ThemeSystem.Theme.textPrimary
                                            font.pixelSize: 30
                                            font.bold: true
                                            wrapMode: Text.WordWrap
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }

                                        Text {
                                            text: "先建立服务端连接，再恢复你的桌面会话。"
                                            color: ThemeSystem.Theme.textSecondary
                                            font.pixelSize: 14
                                            wrapMode: Text.WordWrap
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        radius: ThemeSystem.Theme.radiusMedium
                                        color: "#eff6ff"
                                        border.width: 1
                                        border.color: "#bfdbfe"
                                        implicitHeight: helperText.implicitHeight + 20

                                        Text {
                                            id: helperText
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            text: "如果你启用了代理，可在进入客户端后的设置页里填写，例如 socks5://127.0.0.1:1080。"
                                            wrapMode: Text.WordWrap
                                            color: ThemeSystem.Theme.textPrimary
                                            font.pixelSize: 13
                                            font.family: ThemeSystem.Theme.fontFamily
                                        }
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

                                    Rectangle {
                                        visible: loginViewModel.busy
                                        Layout.fillWidth: true
                                        radius: ThemeSystem.Theme.radiusMedium
                                        color: "#f0fdf4"
                                        border.width: 1
                                        border.color: "#86efac"
                                        implicitHeight: busyRow.implicitHeight + 22

                                        RowLayout {
                                            id: busyRow
                                            anchors.fill: parent
                                            anchors.margins: 12
                                            spacing: 12

                                            BusyIndicator {
                                                running: loginViewModel.busy
                                                visible: loginViewModel.busy
                                                implicitWidth: 22
                                                implicitHeight: 22
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "正在验证账号并准备进入桌面端。"
                                                color: ThemeSystem.Theme.textPrimary
                                                font.pixelSize: 13
                                                wrapMode: Text.WordWrap
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }
                                        }
                                    }

                                    Item {
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 6
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

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: "Desktop Qt Beta 通过独立更新通道发布，登录后可在设置页查看版本与更新状态。"
                            color: ThemeSystem.Theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignHCenter
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }
                }
            }
        }
    }
}
