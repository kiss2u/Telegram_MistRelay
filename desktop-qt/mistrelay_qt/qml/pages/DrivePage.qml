import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
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
        case "primary":
            return ThemeSystem.Theme.colorPrimary
        default:
            return ThemeSystem.Theme.colorInfo
        }
    }

    function toneSoftColor(tone) {
        switch (tone) {
        case "success":
            return ThemeSystem.Theme.successSoft
        case "warning":
            return ThemeSystem.Theme.warningSoft
        case "danger":
            return ThemeSystem.Theme.dangerSoft
        case "primary":
            return "#eef2ff"
        default:
            return ThemeSystem.Theme.infoSoft
        }
    }

    property var filterOptions: [
        { label: "全部", value: "all" },
        { label: "视频", value: "videos" },
        { label: "图片", value: "images" },
        { label: "文档", value: "documents" }
    ]

    MediaPlayer {
        id: previewPlayer
        autoPlay: true
        audioOutput: AudioOutput { }
        videoOutput: previewVideoOutput
        source: driveViewModel.previewState.mode === "video" ? driveViewModel.previewState.source : ""
    }

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: ThemeSystem.Theme.sectionSpacing

        GlassCard {
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 12

                Text {
                    text: "Telegram 网盘"
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: driveViewModel.subtitle
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 14
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: driveViewModel.usageSummary
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 13
                    font.family: ThemeSystem.Theme.fontFamily
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    AppTextField {
                        Layout.fillWidth: true
                        text: driveViewModel.searchKeyword
                        placeholderText: "搜索文件名或 Telegram 标题"
                        onTextEdited: driveViewModel.setSearchKeyword(text)
                        onAccepted: driveViewModel.commitSearch()
                    }

                    PrimaryButton {
                        text: driveViewModel.busy ? "同步中..." : "搜索 / 刷新"
                        enabled: !driveViewModel.busy
                        onClicked: driveViewModel.commitSearch()
                    }

                    Button {
                        visible: driveViewModel.searchKeyword.length > 0
                        text: "清空搜索"
                        onClicked: driveViewModel.clearSearch()
                    }

                    Button {
                        text: "清空 Telegram"
                        onClicked: driveViewModel.clearTelegramMedia()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: root.filterOptions

                        delegate: Button {
                            id: filterButton
                            required property var modelData

                            text: modelData.label
                            checkable: true
                            checked: driveViewModel.currentFilter === modelData.value
                            onClicked: driveViewModel.setCurrentFilter(modelData.value)

                            background: Rectangle {
                                radius: ThemeSystem.Theme.radiusMedium
                                color: filterButton.checked ? ThemeSystem.Theme.colorPrimary : "#ffffff"
                                border.width: 1
                                border.color: filterButton.checked ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor
                            }

                            contentItem: Text {
                                text: filterButton.text
                                color: filterButton.checked ? "#ffffff" : ThemeSystem.Theme.textPrimary
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                font.bold: filterButton.checked
                                font.family: ThemeSystem.Theme.fontFamily
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        visible: driveViewModel.canNavigateUp
                        text: "返回上级"
                        onClicked: driveViewModel.navigateUp()
                    }
                }

                Rectangle {
                    visible: driveViewModel.infoMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.successSoft
                    border.width: 1
                    border.color: "#86efac"
                    implicitHeight: driveInfoLabel.implicitHeight + 20

                    Text {
                        id: driveInfoLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: driveViewModel.infoMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                Rectangle {
                    visible: driveViewModel.errorMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.dangerSoft
                    border.width: 1
                    border.color: "#fca5a5"
                    implicitHeight: driveErrorLabel.implicitHeight + 20

                    Text {
                        id: driveErrorLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: driveViewModel.errorMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 760
            spacing: 18

            GlassCard {
                Layout.fillWidth: true
                Layout.fillHeight: true
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Text {
                            text: driveViewModel.currentPathLabel
                            color: ThemeSystem.Theme.textPrimary
                            font.pixelSize: 18
                            font.bold: true
                            font.family: ThemeSystem.Theme.fontFamily
                            Layout.fillWidth: true
                        }

                        Text {
                            text: driveViewModel.filterSummary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true

                        Column {
                            width: parent.width
                            spacing: 12

                            Repeater {
                                model: driveViewModel.itemsModel

                                delegate: Rectangle {
                                    required property string path
                                    required property string title
                                    required property string kind
                                    required property string subtitle
                                    required property string metaPrimary
                                    required property string metaSecondary
                                    required property string sizeText
                                    required property string timeText
                                    required property string tone
                                    required property bool isDir
                                    required property bool canPreview
                                    required property bool canDownload
                                    required property bool canDelete

                                    width: parent.width
                                    implicitHeight: itemLayout.implicitHeight + 24
                                    radius: ThemeSystem.Theme.radiusLarge
                                    color: driveViewModel.selectedItem.path === path ? "#f8fbff" : "#ffffff"
                                    border.width: 1
                                    border.color: driveViewModel.selectedItem.path === path ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor

                                    RowLayout {
                                        id: itemLayout
                                        anchors.fill: parent
                                        anchors.margins: 12
                                        spacing: 14
                                        z: 1

                                        Rectangle {
                                            radius: ThemeSystem.Theme.radiusMedium
                                            color: root.toneSoftColor(tone)
                                            border.width: 1
                                            border.color: root.toneColor(tone)
                                            implicitWidth: 96
                                            implicitHeight: 84

                                            Text {
                                                anchors.centerIn: parent
                                                text: isDir ? "组" : (kind === "video" ? "视频" : (kind === "image" ? "图片" : "文档"))
                                                color: root.toneColor(tone)
                                                font.pixelSize: 18
                                                font.bold: true
                                                font.family: ThemeSystem.Theme.fontFamily
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 10

                                                Text {
                                                    text: title
                                                    color: ThemeSystem.Theme.textPrimary
                                                    font.pixelSize: 15
                                                    font.bold: true
                                                    font.family: ThemeSystem.Theme.fontFamily
                                                    elide: Text.ElideRight
                                                    Layout.fillWidth: true
                                                }

                                                Rectangle {
                                                    radius: 999
                                                    color: root.toneSoftColor(tone)
                                                    border.width: 1
                                                    border.color: root.toneColor(tone)
                                                    implicitHeight: 28
                                                    implicitWidth: itemToneText.implicitWidth + 18

                                                    Text {
                                                        id: itemToneText
                                                        anchors.centerIn: parent
                                                        text: isDir ? "媒体组" : (kind === "video" ? "视频" : (kind === "image" ? "图片" : "文档"))
                                                        color: root.toneColor(tone)
                                                        font.pixelSize: 12
                                                        font.bold: true
                                                        font.family: ThemeSystem.Theme.fontFamily
                                                    }
                                                }
                                            }

                                            Text {
                                                text: subtitle
                                                color: ThemeSystem.Theme.textSecondary
                                                font.pixelSize: 13
                                                font.family: ThemeSystem.Theme.fontFamily
                                                wrapMode: Text.WordWrap
                                                Layout.fillWidth: true
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 12

                                                Text {
                                                    text: sizeText
                                                    color: ThemeSystem.Theme.textSecondary
                                                    font.pixelSize: 12
                                                    font.family: ThemeSystem.Theme.fontFamily
                                                }

                                                Text {
                                                    text: timeText
                                                    color: ThemeSystem.Theme.textTertiary
                                                    font.pixelSize: 12
                                                    font.family: ThemeSystem.Theme.fontFamily
                                                    Layout.fillWidth: true
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            spacing: 8

                                            Button {
                                                visible: isDir
                                                text: "进入"
                                                onClicked: driveViewModel.activateItem(path)
                                            }

                                            Button {
                                                visible: !isDir && canPreview
                                                text: "预览"
                                                onClicked: driveViewModel.openPreview(path)
                                            }

                                            Button {
                                                visible: canDownload
                                                text: isDir ? "下载整组" : "下载"
                                                onClicked: driveViewModel.downloadItem(path)
                                            }

                                            Button {
                                                visible: canDelete
                                                text: isDir ? "删除媒体组" : "删除"
                                                onClicked: driveViewModel.deleteItem(path)
                                            }
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        acceptedButtons: Qt.LeftButton
                                        onClicked: {
                                            if (isDir) {
                                                driveViewModel.activateItem(path)
                                            } else {
                                                driveViewModel.selectItem(path)
                                            }
                                        }
                                        onDoubleClicked: {
                                            if (!isDir) {
                                                driveViewModel.openPreview(path)
                                            }
                                        }
                                    }
                                }
                            }

                            Text {
                                visible: driveViewModel.itemsModel.count === 0
                                width: parent.width
                                text: driveViewModel.emptyState
                                wrapMode: Text.WordWrap
                                color: ThemeSystem.Theme.textSecondary
                                font.pixelSize: 14
                                font.family: ThemeSystem.Theme.fontFamily
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.preferredWidth: 390
                Layout.fillHeight: true
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    Text {
                        text: driveViewModel.selectedItem.hasSelection ? "详情与预览" : "预览器"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: driveViewModel.selectedItem.hasSelection ? driveViewModel.selectedItem.title : "尚未选择项目"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 16
                        font.bold: true
                        wrapMode: Text.WordWrap
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: driveViewModel.selectedItem.subtitle
                        color: ThemeSystem.Theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            radius: ThemeSystem.Theme.radiusMedium
                            color: "#f8fafc"
                            border.width: 1
                            border.color: ThemeSystem.Theme.lineColor
                            Layout.fillWidth: true
                            implicitHeight: 58

                            Column {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Text {
                                    text: "大小"
                                    color: ThemeSystem.Theme.textTertiary
                                    font.pixelSize: 11
                                    font.family: ThemeSystem.Theme.fontFamily
                                }

                                Text {
                                    text: driveViewModel.selectedItem.metaPrimary
                                    color: ThemeSystem.Theme.textPrimary
                                    font.pixelSize: 13
                                    font.bold: true
                                    font.family: ThemeSystem.Theme.fontFamily
                                }
                            }
                        }

                        Rectangle {
                            radius: ThemeSystem.Theme.radiusMedium
                            color: "#f8fafc"
                            border.width: 1
                            border.color: ThemeSystem.Theme.lineColor
                            Layout.fillWidth: true
                            implicitHeight: 58

                            Column {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 4

                                Text {
                                    text: "时间"
                                    color: ThemeSystem.Theme.textTertiary
                                    font.pixelSize: 11
                                    font.family: ThemeSystem.Theme.fontFamily
                                }

                                Text {
                                    text: driveViewModel.selectedItem.metaSecondary
                                    color: ThemeSystem.Theme.textPrimary
                                    font.pixelSize: 13
                                    font.bold: true
                                    elide: Text.ElideRight
                                    font.family: ThemeSystem.Theme.fontFamily
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Button {
                            visible: driveViewModel.selectedItem.canPreview
                            text: "开始预览"
                            onClicked: driveViewModel.openPreview(driveViewModel.selectedItem.path)
                        }

                        Button {
                            visible: driveViewModel.selectedItem.canDownload
                            text: driveViewModel.selectedItem.isDir ? "下载整组" : "下载到本地"
                            onClicked: driveViewModel.downloadItem(driveViewModel.selectedItem.path)
                        }

                        Button {
                            visible: driveViewModel.selectedItem.canDelete
                            text: driveViewModel.selectedItem.isDir ? "删除媒体组" : "删除"
                            onClicked: driveViewModel.deleteSelected()
                        }

                        Button {
                            visible: driveViewModel.previewState.mode !== "none"
                            text: "关闭预览"
                            onClicked: driveViewModel.closePreview()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: ThemeSystem.Theme.radiusLarge
                        color: "#0f172a"
                        border.width: 1
                        border.color: "#1e293b"

                        Item {
                            anchors.fill: parent

                            Image {
                                anchors.fill: parent
                                anchors.margins: 12
                                visible: driveViewModel.previewState.mode === "image" && driveViewModel.previewState.source.length > 0
                                source: driveViewModel.previewState.source
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                cache: false
                            }

                            VideoOutput {
                                id: previewVideoOutput
                                anchors.fill: parent
                                anchors.margins: 12
                                visible: driveViewModel.previewState.mode === "video" && driveViewModel.previewState.source.length > 0
                                fillMode: VideoOutput.PreserveAspectFit
                            }

                            Column {
                                anchors.centerIn: parent
                                width: parent.width - 48
                                spacing: 10
                                visible: driveViewModel.previewState.mode === "none" || driveViewModel.previewState.source.length === 0

                                Text {
                                    width: parent.width
                                    text: driveViewModel.previewState.status
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignHCenter
                                    color: "#e2e8f0"
                                    font.pixelSize: 18
                                    font.bold: true
                                    font.family: ThemeSystem.Theme.fontFamily
                                }

                                Text {
                                    width: parent.width
                                    text: driveViewModel.previewState.info
                                    wrapMode: Text.WordWrap
                                    horizontalAlignment: Text.AlignHCenter
                                    color: "#94a3b8"
                                    font.pixelSize: 13
                                    font.family: ThemeSystem.Theme.fontFamily
                                }
                            }

                            Rectangle {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 12
                                visible: driveViewModel.previewState.mode !== "none"
                                radius: ThemeSystem.Theme.radiusMedium
                                color: "#0f172acc"
                                border.width: 1
                                border.color: "#334155"
                                implicitHeight: previewStatusColumn.implicitHeight + 20

                                Column {
                                    id: previewStatusColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 4

                                    Text {
                                        width: parent.width
                                        text: driveViewModel.previewState.status
                                        color: "#e2e8f0"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 13
                                        font.bold: true
                                        font.family: ThemeSystem.Theme.fontFamily
                                    }

                                    Text {
                                        width: parent.width
                                        text: driveViewModel.previewState.info
                                        color: "#94a3b8"
                                        wrapMode: Text.WordWrap
                                        font.pixelSize: 12
                                        font.family: ThemeSystem.Theme.fontFamily
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
