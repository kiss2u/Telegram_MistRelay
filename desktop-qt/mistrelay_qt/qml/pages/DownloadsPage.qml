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

    property var taskStatusOptions: [
        { label: "全部", value: "all" },
        { label: "活跃", value: "active" },
        { label: "已完成", value: "completed" },
        { label: "失败", value: "failed" }
    ]

    property var queueTypeOptions: [
        { label: "全部类型", value: "all" },
        { label: "媒体组", value: "media_group" },
        { label: "单文件", value: "single" }
    ]

    property var localStatusOptions: [
        { label: "全部状态", value: "all" },
        { label: "进行中", value: "active" },
        { label: "已完成", value: "completed" },
        { label: "失败/取消", value: "failed" }
    ]

    Component {
        id: filterChip

        Button {
            id: chip

            required property string label
            required property string value
            required property string currentValue

            text: label
            checkable: true
            checked: currentValue === value

            background: Rectangle {
                radius: ThemeSystem.Theme.radiusMedium
                color: chip.checked ? ThemeSystem.Theme.colorPrimary : "#ffffff"
                border.width: 1
                border.color: chip.checked ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor
            }

            contentItem: Text {
                text: chip.text
                color: chip.checked ? "#ffffff" : ThemeSystem.Theme.textPrimary
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: chip.checked
                font.family: ThemeSystem.Theme.fontFamily
            }
        }
    }

    Component {
        id: taskActionCard

        Rectangle {
            Layout.fillWidth: true
            radius: ThemeSystem.Theme.radiusLarge
            color: "#ffffff"
            border.width: 1
            border.color: ThemeSystem.Theme.lineColor
            implicitHeight: contentLayout.implicitHeight + 24

            RowLayout {
                id: contentLayout
                anchors.fill: parent
                anchors.margins: 12
                spacing: 14

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
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        Rectangle {
                            radius: 999
                            color: root.toneSoftColor(statusTone)
                            border.width: 1
                            border.color: root.toneColor(statusTone)
                            implicitHeight: 28
                            implicitWidth: statusText.implicitWidth + 18

                            Text {
                                id: statusText
                                anchors.centerIn: parent
                                text: statusLabel
                                color: root.toneColor(statusTone)
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
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: progressPercent
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
                            text: metaPrimary
                            color: ThemeSystem.Theme.textSecondary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        Text {
                            text: metaSecondary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    Text {
                        visible: error.length > 0
                        text: error
                        color: ThemeSystem.Theme.colorDanger
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    spacing: 8

                    Button {
                        visible: rowType === "download" && canRetry
                        text: "重试下载"
                        onClicked: downloadsViewModel.retryServerDownload(gid)
                    }

                    Button {
                        visible: rowType === "download" && canDelete
                        text: "删除任务"
                        onClicked: downloadsViewModel.deleteServerDownload(gid)
                    }

                    Button {
                        visible: rowType === "upload" && canRetry
                        text: "重试上传"
                        onClicked: downloadsViewModel.retryUpload(uploadId)
                    }

                    Button {
                        visible: rowType === "upload" && canDelete
                        text: "删除上传"
                        onClicked: downloadsViewModel.deleteUpload(uploadId)
                    }
                }
            }
        }
    }

    Component {
        id: queueCard

        Rectangle {
            Layout.fillWidth: true
            radius: ThemeSystem.Theme.radiusLarge
            color: "#ffffff"
            border.width: 1
            border.color: ThemeSystem.Theme.lineColor
            implicitHeight: queueContent.implicitHeight + 24

            ColumnLayout {
                id: queueContent
                anchors.fill: parent
                anchors.margins: 12
                spacing: 6

                RowLayout {
                    Layout.fillWidth: true

                    Text {
                        text: title
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 15
                        font.bold: true
                        Layout.fillWidth: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Rectangle {
                        radius: 999
                        color: root.toneSoftColor(statusTone)
                        border.width: 1
                        border.color: root.toneColor(statusTone)
                        implicitHeight: 28
                        implicitWidth: statusBadgeText.implicitWidth + 18

                        Text {
                            id: statusBadgeText
                            anchors.centerIn: parent
                            text: statusLabel
                            color: root.toneColor(statusTone)
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
                    wrapMode: Text.WordWrap
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: meta
                    color: ThemeSystem.Theme.textTertiary
                    font.pixelSize: 12
                    font.family: ThemeSystem.Theme.fontFamily
                }
            }
        }
    }

    Component {
        id: localCard

        Rectangle {
            Layout.fillWidth: true
            radius: ThemeSystem.Theme.radiusLarge
            color: "#ffffff"
            border.width: 1
            border.color: ThemeSystem.Theme.lineColor
            implicitHeight: localContent.implicitHeight + 24

            RowLayout {
                id: localContent
                anchors.fill: parent
                anchors.margins: 12
                spacing: 14

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
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        Rectangle {
                            radius: 999
                            color: root.toneSoftColor(statusTone)
                            border.width: 1
                            border.color: root.toneColor(statusTone)
                            implicitHeight: 28
                            implicitWidth: localStatusText.implicitWidth + 18

                            Text {
                                id: localStatusText
                                anchors.centerIn: parent
                                text: statusLabel
                                color: root.toneColor(statusTone)
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
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    ProgressBar {
                        Layout.fillWidth: true
                        from: 0
                        to: 100
                        value: progressPercent
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
                            text: metaPrimary
                            color: ThemeSystem.Theme.textSecondary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        Text {
                            text: metaSecondary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    Text {
                        visible: error.length > 0
                        text: error
                        color: ThemeSystem.Theme.colorDanger
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    spacing: 8

                    Button {
                        visible: canCancel
                        text: "取消"
                        onClicked: downloadsViewModel.cancelLocalDownload(transferId)
                    }

                    Button {
                        visible: canRetry
                        text: "重试"
                        onClicked: downloadsViewModel.retryLocalDownload(transferId)
                    }

                    Button {
                        visible: canOpen
                        text: "打开文件"
                        onClicked: downloadsViewModel.openLocalFile(localPath)
                    }

                    Button {
                        visible: canOpen
                        text: "打开目录"
                        onClicked: downloadsViewModel.showLocalFileInFolder(localPath)
                    }

                    Button {
                        visible: canDelete
                        text: "删除"
                        onClicked: downloadsViewModel.removeLocalDownload(transferId)
                    }
                }
            }
        }
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
                    text: "任务中心"
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: downloadsViewModel.headline
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    font.family: ThemeSystem.Theme.fontFamily
                }

                RowLayout {
                    spacing: 10

                    Repeater {
                        model: [
                            { label: "任务中心", value: "tasks" },
                            { label: "任务队列", value: "queue" },
                            { label: "本地下载", value: "local" }
                        ]

                        delegate: Loader {
                            sourceComponent: filterChip

                            onLoaded: {
                                item.label = modelData.label
                                item.value = modelData.value
                                item.currentValue = Qt.binding(function() {
                                    return downloadsViewModel.currentTab
                                })
                                item.clicked.connect(function() {
                                    downloadsViewModel.setCurrentTab(modelData.value)
                                })
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    PrimaryButton {
                        text: downloadsViewModel.busy ? "刷新中..." : "刷新"
                        enabled: !downloadsViewModel.busy
                        onClicked: downloadsViewModel.refresh()
                    }
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width > 1080 ? 4 : 2
            columnSpacing: 18
            rowSpacing: 18

            Repeater {
                model: downloadsViewModel.summaryCards

                delegate: StatCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 180
                    title: modelData.title
                    value: modelData.value
                    caption: modelData.caption
                    tone: modelData.tone
                }
            }
        }

        GlassCard {
            Layout.fillWidth: true
            backgroundColor: "#ffffffff"

            ColumnLayout {
                anchors.fill: parent
                spacing: 14

                Text {
                    text: downloadsViewModel.runtimeNote
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Rectangle {
                    visible: downloadsViewModel.infoMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.successSoft
                    border.width: 1
                    border.color: "#86efac"
                    implicitHeight: infoLabel.implicitHeight + 20

                    Text {
                        id: infoLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: downloadsViewModel.infoMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                Rectangle {
                    visible: downloadsViewModel.errorMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.dangerSoft
                    border.width: 1
                    border.color: "#fca5a5"
                    implicitHeight: errorLabel.implicitHeight + 20

                    Text {
                        id: errorLabel
                        anchors.fill: parent
                        anchors.margins: 10
                        text: downloadsViewModel.errorMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    visible: downloadsViewModel.currentTab === "tasks"
                    Layout.fillWidth: true
                    spacing: 16

                    AppTextField {
                        Layout.fillWidth: true
                        text: downloadsViewModel.taskKeyword
                        placeholderText: "搜索文件名、来源、状态"
                        onTextEdited: downloadsViewModel.setTaskKeyword(text)
                    }

                    RowLayout {
                        spacing: 8

                        Repeater {
                            model: root.taskStatusOptions

                            delegate: Loader {
                                sourceComponent: filterChip

                                onLoaded: {
                                    item.label = modelData.label
                                    item.value = modelData.value
                                    item.currentValue = Qt.binding(function() {
                                        return downloadsViewModel.taskStatusFilter
                                    })
                                    item.clicked.connect(function() {
                                        downloadsViewModel.setTaskStatusFilter(modelData.value)
                                    })
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        Text {
                            text: downloadsViewModel.taskFilterSummary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    Text {
                        text: "活跃下载"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: downloadsViewModel.activeDownloadsModel

                        delegate: taskActionCard
                    }

                    Text {
                        visible: downloadsViewModel.activeDownloadsModel.count === 0
                        text: "当前没有匹配的下载任务。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "活跃上传"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: downloadsViewModel.activeUploadsModel

                        delegate: taskActionCard
                    }

                    Text {
                        visible: downloadsViewModel.activeUploadsModel.count === 0
                        text: "当前没有匹配的上传任务。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "记录组"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: downloadsViewModel.groupRecordsModel

                        delegate: taskActionCard
                    }

                    Text {
                        visible: downloadsViewModel.groupRecordsModel.count === 0
                        text: "当前没有匹配的记录组。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    visible: downloadsViewModel.currentTab === "queue"
                    Layout.fillWidth: true
                    spacing: 16

                    AppTextField {
                        Layout.fillWidth: true
                        text: downloadsViewModel.queueKeyword
                        placeholderText: "搜索队列标题"
                        onTextEdited: downloadsViewModel.setQueueKeyword(text)
                    }

                    RowLayout {
                        spacing: 8

                        Repeater {
                            model: root.queueTypeOptions

                            delegate: Loader {
                                sourceComponent: filterChip

                                onLoaded: {
                                    item.label = modelData.label
                                    item.value = modelData.value
                                    item.currentValue = Qt.binding(function() {
                                        return downloadsViewModel.queueTypeFilter
                                    })
                                    item.clicked.connect(function() {
                                        downloadsViewModel.setQueueTypeFilter(modelData.value)
                                    })
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        Text {
                            text: downloadsViewModel.queueFilterSummary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    Rectangle {
                        visible: downloadsViewModel.queueFloodWaitText.length > 0
                        Layout.fillWidth: true
                        radius: ThemeSystem.Theme.radiusMedium
                        color: ThemeSystem.Theme.warningSoft
                        border.width: 1
                        border.color: "#fcd34d"
                        implicitHeight: floodWaitText.implicitHeight + 20

                        Text {
                            id: floodWaitText
                            anchors.fill: parent
                            anchors.margins: 10
                            text: downloadsViewModel.queueFloodWaitText
                            wrapMode: Text.WordWrap
                            color: ThemeSystem.Theme.textPrimary
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    Text {
                        text: "正在处理"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: downloadsViewModel.queueCurrentModel

                        delegate: queueCard
                    }

                    Text {
                        visible: downloadsViewModel.queueCurrentModel.count === 0
                        text: "当前没有处理中任务。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "等待队列"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Repeater {
                        model: downloadsViewModel.queueWaitingModel

                        delegate: queueCard
                    }

                    Text {
                        visible: downloadsViewModel.queueWaitingModel.count === 0
                        text: "当前没有等待中的队列任务。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                ColumnLayout {
                    visible: downloadsViewModel.currentTab === "local"
                    Layout.fillWidth: true
                    spacing: 16

                    AppTextField {
                        Layout.fillWidth: true
                        text: downloadsViewModel.localKeyword
                        placeholderText: "搜索文件名、保存位置、错误信息"
                        onTextEdited: downloadsViewModel.setLocalKeyword(text)
                    }

                    RowLayout {
                        spacing: 8

                        Repeater {
                            model: root.localStatusOptions

                            delegate: Loader {
                                sourceComponent: filterChip

                                onLoaded: {
                                    item.label = modelData.label
                                    item.value = modelData.value
                                    item.currentValue = Qt.binding(function() {
                                        return downloadsViewModel.localStatusFilter
                                    })
                                    item.clicked.connect(function() {
                                        downloadsViewModel.setLocalStatusFilter(modelData.value)
                                    })
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        Text {
                            text: downloadsViewModel.localFilterSummary
                            color: ThemeSystem.Theme.textTertiary
                            font.pixelSize: 12
                            font.family: ThemeSystem.Theme.fontFamily
                        }
                    }

                    Repeater {
                        model: downloadsViewModel.localDownloadsModel

                        delegate: localCard
                    }

                    Text {
                        visible: downloadsViewModel.localDownloadsModel.count === 0
                        text: "当前没有匹配的本地下载任务。"
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }
            }
        }
    }
}
