import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem
import "../components"

Flickable {
    id: root

    clip: true
    contentWidth: width
    contentHeight: contentColumn.implicitHeight

    function toneColor(tone) {
        switch (tone) {
        case "success":
            return ThemeSystem.Theme.colorSuccess
        case "warning":
            return ThemeSystem.Theme.colorWarning
        case "danger":
            return ThemeSystem.Theme.colorDanger
        default:
            return ThemeSystem.Theme.colorPrimary
        }
    }

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: ThemeSystem.Theme.sectionSpacing

        GlassCard {
            Layout.fillWidth: true
            backgroundColor: "#f8fbffd6"

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Text {
                    text: "运行概览"
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: dashboardViewModel.subtitle
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 14
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: "#ffffff"
                    border.width: 1
                    border.color: ThemeSystem.Theme.lineColor
                    implicitHeight: trendText.implicitHeight + 22

                    Text {
                        id: trendText
                        anchors.fill: parent
                        anchors.margins: 11
                        text: dashboardViewModel.trendSummary
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 13
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                RowLayout {
                    spacing: 12

                    PrimaryButton {
                        text: dashboardViewModel.busy ? "同步中..." : "刷新概览"
                        enabled: !dashboardViewModel.busy
                        onClicked: dashboardViewModel.refresh()
                    }

                    Text {
                        text: dashboardViewModel.lastUpdated.length > 0
                              ? "最近更新：" + dashboardViewModel.lastUpdated
                              : "尚未同步"
                        color: ThemeSystem.Theme.textTertiary
                        font.pixelSize: 13
                        font.family: ThemeSystem.Theme.fontFamily
                        Layout.alignment: Qt.AlignVCenter
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width > 1180 ? 4 : 2
            columnSpacing: 18
            rowSpacing: 18

            Repeater {
                model: dashboardViewModel.statCards

                delegate: StatCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 190
                    title: modelData.title
                    value: modelData.value
                    caption: modelData.caption
                    tone: modelData.tone
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            Repeater {
                model: dashboardViewModel.resourceCards

                delegate: GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 182
                    backgroundColor: "#ffffffff"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: modelData.title
                                color: ThemeSystem.Theme.textPrimary
                                font.pixelSize: 18
                                font.bold: true
                                font.family: ThemeSystem.Theme.fontFamily
                                Layout.fillWidth: true
                            }

                            Text {
                                text: modelData.value
                                color: root.toneColor(modelData.tone)
                                font.pixelSize: 18
                                font.bold: true
                                font.family: ThemeSystem.Theme.fontFamily
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 10
                            radius: 5
                            color: "#edf2f7"

                            Rectangle {
                                width: parent.width * Math.max(0, Math.min(1, (modelData.percent || 0) / 100))
                                height: parent.height
                                radius: parent.radius
                                color: root.toneColor(modelData.tone)
                            }
                        }

                        Text {
                            text: modelData.caption
                            color: ThemeSystem.Theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    Text {
                        text: "系统信息"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: dashboardViewModel.systemInfo

                        delegate: RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: modelData.label
                                color: ThemeSystem.Theme.textSecondary
                                font.pixelSize: 13
                                font.family: ThemeSystem.Theme.fontFamily
                                Layout.preferredWidth: 120
                            }

                            Text {
                                text: modelData.value
                                color: ThemeSystem.Theme.textPrimary
                                font.pixelSize: 14
                                font.bold: true
                                font.family: ThemeSystem.Theme.fontFamily
                                Layout.fillWidth: true
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 220
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 12

                    Text {
                        text: "状态说明"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "Dashboard 已接入下载、上传、队列、系统资源和监控趋势数据。实时状态流会触发自动刷新，首次 Beta 保持轻量展示，不额外引入桌面图表依赖。"
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textSecondary
                        font.pixelSize: 14
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        visible: dashboardViewModel.errorMessage.length > 0
                        text: dashboardViewModel.errorMessage
                        color: ThemeSystem.Theme.colorDanger
                        wrapMode: Text.WordWrap
                        font.pixelSize: 13
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }
            }
        }
    }
}
