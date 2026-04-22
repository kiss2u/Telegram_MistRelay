import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem
import "../components"

ResponsivePage {
    id: root

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

    readonly property int statColumns: compact ? 1 : (wide ? 4 : 2)
    readonly property int resourceColumns: compact ? 1 : (wide ? 3 : 2)

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
                wrapMode: Text.WordWrap
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

            GridLayout {
                Layout.fillWidth: true
                columns: root.compact ? 1 : 2
                columnSpacing: 12
                rowSpacing: 12

                PrimaryButton {
                    text: dashboardViewModel.busy ? "同步中..." : "刷新概览"
                    enabled: !dashboardViewModel.busy
                    Layout.fillWidth: root.compact
                    onClicked: dashboardViewModel.refresh()
                }

                Text {
                    text: dashboardViewModel.lastUpdated.length > 0
                          ? "最近更新：" + dashboardViewModel.lastUpdated
                          : "尚未同步"
                    color: ThemeSystem.Theme.textTertiary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    font.family: ThemeSystem.Theme.fontFamily
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                }
            }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.statColumns
        columnSpacing: 18
        rowSpacing: 18

        Repeater {
            model: dashboardViewModel.statCards

            delegate: StatCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 190
                Layout.alignment: Qt.AlignTop
                title: modelData.title
                value: modelData.value
                caption: modelData.caption
                tone: modelData.tone
            }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: root.resourceColumns
        columnSpacing: 18
        rowSpacing: 18

        Repeater {
            model: dashboardViewModel.resourceCards

            delegate: GlassCard {
                Layout.fillWidth: true
                Layout.preferredHeight: 182
                Layout.alignment: Qt.AlignTop
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
                            wrapMode: Text.WordWrap
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

    GridLayout {
        Layout.fillWidth: true
        columns: root.compact ? 1 : 2
        columnSpacing: 18
        rowSpacing: 18

        GlassCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            Layout.alignment: Qt.AlignTop
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

                    delegate: GridLayout {
                        Layout.fillWidth: true
                        columns: root.compact ? 1 : 2
                        columnSpacing: 12
                        rowSpacing: 4

                        Text {
                            text: modelData.label
                            color: ThemeSystem.Theme.textSecondary
                            font.pixelSize: 13
                            font.family: ThemeSystem.Theme.fontFamily
                            Layout.minimumWidth: root.compact ? 0 : 120
                        }

                        Text {
                            text: modelData.value
                            color: ThemeSystem.Theme.textPrimary
                            font.pixelSize: 14
                            font.bold: true
                            font.family: ThemeSystem.Theme.fontFamily
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        GlassCard {
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            Layout.alignment: Qt.AlignTop
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
