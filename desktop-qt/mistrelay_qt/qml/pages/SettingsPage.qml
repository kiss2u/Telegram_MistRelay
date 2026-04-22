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

    property string scope: "client"
    property string clientTab: "connection"
    property string serverCategory: "telegram"
    property string managementTab: "docker"

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

    Component.onCompleted: settingsViewModel.bootstrap()
    onServerCategoryChanged: {
        settingsViewModel.loadServerCategory(serverCategory)
        if (serverCategory === "rclone") {
            settingsViewModel.loadRcloneConfigFile()
        }
    }

    component ScopeButton: Button {
        id: scopeButton
        required property string buttonValue
        required property string buttonLabel

        text: buttonLabel
        checkable: true
        checked: root.scope === buttonValue
        onClicked: root.scope = buttonValue

        background: Rectangle {
            radius: ThemeSystem.Theme.radiusMedium
            color: scopeButton.checked ? ThemeSystem.Theme.colorPrimary : "#ffffff"
            border.width: 1
            border.color: scopeButton.checked ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor
        }

        contentItem: Text {
            text: scopeButton.text
            color: scopeButton.checked ? "#ffffff" : ThemeSystem.Theme.textPrimary
            font.bold: scopeButton.checked
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: ThemeSystem.Theme.fontFamily
        }
    }

    component FilterButton: Button {
        id: filterButton
        required property bool activeState

        checkable: true
        checked: activeState

        background: Rectangle {
            radius: ThemeSystem.Theme.radiusMedium
            color: filterButton.checked ? ThemeSystem.Theme.colorPrimary : "#ffffff"
            border.width: 1
            border.color: filterButton.checked ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor
        }

        contentItem: Text {
            text: filterButton.text
            color: filterButton.checked ? "#ffffff" : ThemeSystem.Theme.textPrimary
            font.bold: filterButton.checked
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font.family: ThemeSystem.Theme.fontFamily
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
                spacing: 16

                Text {
                    text: "设置中心"
                    color: ThemeSystem.Theme.textPrimary
                    font.pixelSize: 22
                    font.bold: true
                    font.family: ThemeSystem.Theme.fontFamily
                }

                Text {
                    text: "客户端配置、服务端参数、Docker 运行状态、日志和自动更新现在统一由 PySide 状态层管理。"
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textSecondary
                    font.pixelSize: 14
                    font.family: ThemeSystem.Theme.fontFamily
                }

                RowLayout {
                    spacing: 10

                    ScopeButton {
                        buttonValue: "client"
                        buttonLabel: "客户端设置"
                    }

                    ScopeButton {
                        buttonValue: "server"
                        buttonLabel: "服务端设置"
                    }

                    ScopeButton {
                        buttonValue: "management"
                        buttonLabel: "系统管理"
                    }
                }

                Rectangle {
                    visible: settingsViewModel.infoMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.successSoft
                    border.width: 1
                    border.color: "#86efac"
                    implicitHeight: infoBanner.implicitHeight + 20

                    Text {
                        id: infoBanner
                        anchors.fill: parent
                        anchors.margins: 10
                        text: settingsViewModel.infoMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }

                Rectangle {
                    visible: settingsViewModel.errorMessage.length > 0
                    Layout.fillWidth: true
                    radius: ThemeSystem.Theme.radiusMedium
                    color: ThemeSystem.Theme.dangerSoft
                    border.width: 1
                    border.color: "#fca5a5"
                    implicitHeight: errorBanner.implicitHeight + 20

                    Text {
                        id: errorBanner
                        anchors.fill: parent
                        anchors.margins: 10
                        text: settingsViewModel.errorMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textPrimary
                        font.family: ThemeSystem.Theme.fontFamily
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: scopeLoader.implicitHeight

            Loader {
                id: scopeLoader
                width: parent.width
                sourceComponent: root.scope === "client"
                                 ? clientScope
                                 : root.scope === "server"
                                   ? serverScope
                                   : managementScope
            }
        }
    }

    Component {
        id: clientScope

        ColumnLayout {
            width: root.width
            spacing: ThemeSystem.Theme.sectionSpacing

            GlassCard {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    RowLayout {
                        spacing: 10

                        FilterButton {
                            text: "连接"
                            activeState: root.clientTab === "connection"
                            onClicked: root.clientTab = "connection"
                        }

                        FilterButton {
                            text: "更新"
                            activeState: root.clientTab === "update"
                            onClicked: root.clientTab = "update"
                        }

                        FilterButton {
                            text: "代理"
                            activeState: root.clientTab === "proxy"
                            onClicked: root.clientTab = "proxy"
                        }

                        FilterButton {
                            text: "下载"
                            activeState: root.clientTab === "download"
                            onClicked: root.clientTab = "download"
                        }
                    }

                    Loader {
                        Layout.fillWidth: true
                        sourceComponent: root.clientTab === "connection"
                                         ? clientConnectionTab
                                         : root.clientTab === "update"
                                           ? clientUpdateTab
                                           : root.clientTab === "proxy"
                                             ? clientProxyTab
                                             : clientDownloadTab
                    }
                }
            }
        }
    }

    Component {
        id: clientConnectionTab

        ColumnLayout {
            width: root.width
            spacing: 14

            Text {
                text: "连接设置"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 20
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                text: "这里配置 Qt 客户端要连接的服务端地址，不影响服务器本身参数。"
                wrapMode: Text.WordWrap
                color: ThemeSystem.Theme.textSecondary
                font.family: ThemeSystem.Theme.fontFamily
            }

            AppTextField {
                Layout.fillWidth: true
                text: settingsViewModel.serverBaseUrl
                placeholderText: "https://mistrelay.example.com"
                onTextEdited: settingsViewModel.setServerBaseUrl(text)
            }

            RowLayout {
                spacing: 12

                PrimaryButton {
                    text: "保存连接配置"
                    onClicked: settingsViewModel.save()
                }

                Text {
                    text: settingsViewModel.serverBaseUrl.length > 0
                          ? "当前地址：" + settingsViewModel.serverBaseUrl
                          : "尚未配置服务端地址"
                    color: ThemeSystem.Theme.textSecondary
                    font.family: ThemeSystem.Theme.fontFamily
                    Layout.alignment: Qt.AlignVCenter
                }
            }
        }
    }

    Component {
        id: clientUpdateTab

        ColumnLayout {
            width: root.width
            spacing: 14

            Text {
                text: "更新"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 20
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                text: "当前版本 v" + appVersion
                color: ThemeSystem.Theme.textSecondary
                font.family: ThemeSystem.Theme.fontFamily
            }

            Rectangle {
                Layout.fillWidth: true
                radius: ThemeSystem.Theme.radiusMedium
                color: "#ffffff"
                border.width: 1
                border.color: ThemeSystem.Theme.lineColor
                implicitHeight: updateStateText.implicitHeight + 22

                Text {
                    id: updateStateText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: updateViewModel.updateState
                    wrapMode: Text.WordWrap
                    color: ThemeSystem.Theme.textPrimary
                    font.family: ThemeSystem.Theme.fontFamily
                }
            }

            ProgressBar {
                visible: updateViewModel.updateProgressPercent >= 0
                Layout.fillWidth: true
                from: 0
                to: 100
                value: updateViewModel.updateProgressPercent
            }

            Text {
                visible: updateViewModel.updateNotes.length > 0
                text: updateViewModel.updateNotes
                wrapMode: Text.WordWrap
                color: ThemeSystem.Theme.textSecondary
                font.family: ThemeSystem.Theme.fontFamily
            }

            RowLayout {
                spacing: 12

                PrimaryButton {
                    text: updateViewModel.busy ? "检查中..." : "检查更新"
                    enabled: !updateViewModel.busy
                    onClicked: updateViewModel.checkForUpdates()
                }

                PrimaryButton {
                    visible: updateViewModel.canInstallUpdate
                    text: "更新到 v" + updateViewModel.updateVersion
                    enabled: !updateViewModel.busy
                    onClicked: updateViewModel.installUpdate()
                }

                Button {
                    visible: updateViewModel.manualUrl.length > 0 && !updateViewModel.canInstallUpdate
                    text: "手动下载安装"
                    onClicked: updateViewModel.openManualUpdateUrl()
                }
            }
        }
    }

    Component {
        id: clientProxyTab

        ColumnLayout {
            width: root.width
            spacing: 14

            Text {
                text: "客户端代理"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 20
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            RowLayout {
                spacing: 12

                Switch {
                    checked: settingsViewModel.proxyEnabled
                    onToggled: settingsViewModel.setProxyEnabled(checked)
                }

                Text {
                    text: "启用全局代理"
                    color: ThemeSystem.Theme.textPrimary
                    font.family: ThemeSystem.Theme.fontFamily
                    Layout.alignment: Qt.AlignVCenter
                }
            }

            AppTextField {
                Layout.fillWidth: true
                text: settingsViewModel.proxyUrl
                enabled: settingsViewModel.proxyEnabled
                placeholderText: "http://127.0.0.1:7890 或 socks5://127.0.0.1:1080"
                onTextEdited: settingsViewModel.setProxyUrl(text)
            }

            Text {
                text: "支持 http:// 和 socks5://。启用后，Qt 客户端所有网络流量都会走该代理。"
                wrapMode: Text.WordWrap
                color: ThemeSystem.Theme.textSecondary
                font.family: ThemeSystem.Theme.fontFamily
            }

            PrimaryButton {
                text: "保存代理配置"
                onClicked: settingsViewModel.save()
            }
        }
    }

    Component {
        id: clientDownloadTab

        ColumnLayout {
            width: root.width
            spacing: 14

            Text {
                text: "下载配置"
                color: ThemeSystem.Theme.textPrimary
                font.pixelSize: 20
                font.bold: true
                font.family: ThemeSystem.Theme.fontFamily
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12

                AppTextField {
                    Layout.fillWidth: true
                    text: settingsViewModel.downloadDir
                    placeholderText: "留空则使用系统下载目录下的 MistRelay 文件夹"
                    onTextEdited: settingsViewModel.setDownloadDir(text)
                }

                Button {
                    text: "选择目录"
                    onClicked: settingsViewModel.pickDownloadDir()
                }
            }

            RowLayout {
                spacing: 18

                ColumnLayout {
                    spacing: 8

                    Text {
                        text: "最大并发下载"
                        color: ThemeSystem.Theme.textPrimary
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    SpinBox {
                        from: 1
                        to: 16
                        value: settingsViewModel.maxConcurrentDownloads
                        onValueModified: settingsViewModel.setMaxConcurrentDownloads(value)
                    }
                }

                ColumnLayout {
                    spacing: 8

                    Text {
                        text: "每任务线程数"
                        color: ThemeSystem.Theme.textPrimary
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    SpinBox {
                        from: 1
                        to: 32
                        value: settingsViewModel.threadsPerDownload
                        onValueModified: settingsViewModel.setThreadsPerDownload(value)
                    }
                }
            }

            PrimaryButton {
                text: "保存下载配置"
                onClicked: settingsViewModel.save()
            }
        }
    }

    Component {
        id: serverScope

        ColumnLayout {
            width: root.width
            spacing: ThemeSystem.Theme.sectionSpacing

            GlassCard {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    Text {
                        text: "服务端配置"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 22
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: settingsViewModel.serverStatusMessage
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    RowLayout {
                        spacing: 10

                        Repeater {
                            model: settingsViewModel.serverCategories

                            delegate: FilterButton {
                                required property var modelData

                                text: modelData.label
                                activeState: root.serverCategory === modelData.key
                                onClicked: root.serverCategory = modelData.key
                            }
                        }
                    }

                    RowLayout {
                        spacing: 12

                        PrimaryButton {
                            text: "保存当前分类"
                            onClicked: settingsViewModel.saveServerCategory(root.serverCategory)
                        }

                        Button {
                            text: "重新读取"
                            onClicked: settingsViewModel.loadServerCategory(root.serverCategory)
                        }

                        Button {
                            text: "从 config.yml 重新导入"
                            onClicked: settingsViewModel.reloadServerConfig(root.serverCategory)
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 16

                    Repeater {
                        model: settingsViewModel.serverFieldsModel

                        delegate: ColumnLayout {
                            required property string key
                            required property string label
                            required property string fieldType
                            required property var value

                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: parent.label
                                color: ThemeSystem.Theme.textPrimary
                                font.bold: true
                                font.family: ThemeSystem.Theme.fontFamily
                            }

                            Loader {
                                Layout.fillWidth: true
                                property string fieldKey: parent.key
                                property var fieldValue: parent.value
                                sourceComponent: parent.fieldType === "bool"
                                                 ? boolField
                                                 : parent.fieldType === "multiline"
                                                   ? multilineField
                                                   : parent.fieldType === "int"
                                                     ? intField
                                                     : parent.fieldType === "password"
                                                       ? passwordField
                                                       : textField
                            }
                        }
                    }
                }
            }

            GlassCard {
                visible: root.serverCategory === "rclone"
                Layout.fillWidth: true
                backgroundColor: "#ffffffff"

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    Text {
                        text: "Rclone 配置文件"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    Text {
                        text: "路径：" + settingsViewModel.rcloneConfigPath
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    TextArea {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 260
                        text: settingsViewModel.rcloneConfigText
                        wrapMode: TextArea.NoWrap
                        font.family: "Consolas"
                        onTextChanged: if (activeFocus) settingsViewModel.setRcloneConfigText(text)
                        background: Rectangle {
                            radius: ThemeSystem.Theme.radiusMedium
                            color: "#0f172a"
                            border.width: 1
                            border.color: "#1e293b"
                        }
                        color: "#e2e8f0"
                        selectionColor: ThemeSystem.Theme.colorPrimary
                    }

                    Text {
                        visible: settingsViewModel.rcloneRemotes.length > 0
                        text: "已发现 Remotes：" + settingsViewModel.rcloneRemotes.map(function(item) {
                                  return item.name || item.remote || ""
                              }).filter(function(item) { return item.length > 0 }).join(", ")
                        wrapMode: Text.WordWrap
                        color: ThemeSystem.Theme.textSecondary
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    RowLayout {
                        spacing: 12

                        PrimaryButton {
                            text: "保存 Rclone 配置"
                            onClicked: settingsViewModel.saveRcloneConfigFile()
                        }

                        Button {
                            text: "重新读取"
                            onClicked: settingsViewModel.loadRcloneConfigFile()
                        }
                    }
                }
            }
        }
    }

    Component {
        id: managementScope

        ColumnLayout {
            width: root.width
            spacing: ThemeSystem.Theme.sectionSpacing

            GlassCard {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    RowLayout {
                        spacing: 10

                        FilterButton {
                            text: "Docker / 资源"
                            activeState: root.managementTab === "docker"
                            onClicked: root.managementTab = "docker"
                        }

                        FilterButton {
                            text: "系统日志"
                            activeState: root.managementTab === "app-logs"
                            onClicked: root.managementTab = "app-logs"
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        Button {
                            text: "刷新"
                            onClicked: settingsViewModel.loadManagementSnapshot()
                        }
                    }
                }
            }

            Loader {
                Layout.fillWidth: true
                sourceComponent: root.managementTab === "docker"
                                 ? dockerManagementTab
                                 : appLogsManagementTab
            }
        }
    }

    Component {
        id: dockerManagementTab

        ColumnLayout {
            width: root.width
            spacing: ThemeSystem.Theme.sectionSpacing

            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                Repeater {
                    model: settingsViewModel.resourceCards

                    delegate: GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 170
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
                                wrapMode: Text.WordWrap
                                color: ThemeSystem.Theme.textSecondary
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
                    Layout.preferredHeight: 260
                    backgroundColor: "#ffffffff"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10

                        Text {
                            text: "Docker 状态"
                            color: ThemeSystem.Theme.textPrimary
                            font.pixelSize: 20
                            font.bold: true
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        Repeater {
                            model: [
                                { label: "运行环境", value: settingsViewModel.dockerStatus.in_docker ? "Docker 容器内" : "非 Docker" },
                                { label: "容器名称", value: settingsViewModel.dockerStatus.container_name || "-" },
                                { label: "运行状态", value: settingsViewModel.dockerStatus.status || "-" },
                                { label: "镜像", value: settingsViewModel.dockerStatus.image || "-" },
                                { label: "创建时间", value: settingsViewModel.dockerStatus.created || "-" }
                            ]

                            delegate: RowLayout {
                                Layout.fillWidth: true

                                Text {
                                    text: modelData.label
                                    color: ThemeSystem.Theme.textSecondary
                                    font.family: ThemeSystem.Theme.fontFamily
                                    Layout.preferredWidth: 88
                                }

                                Text {
                                    text: modelData.value
                                    color: ThemeSystem.Theme.textPrimary
                                    font.bold: true
                                    font.family: ThemeSystem.Theme.fontFamily
                                    Layout.fillWidth: true
                                }
                            }
                        }

                        Text {
                            visible: (settingsViewModel.dockerStatus.error || "").length > 0
                            text: settingsViewModel.dockerStatus.error
                            wrapMode: Text.WordWrap
                            color: ThemeSystem.Theme.colorDanger
                            font.family: ThemeSystem.Theme.fontFamily
                        }

                        RowLayout {
                            spacing: 12

                            PrimaryButton {
                                text: "重启容器"
                                onClicked: settingsViewModel.restartDocker()
                            }

                            Button {
                                text: "刷新状态"
                                onClicked: settingsViewModel.loadDockerStatus()
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    backgroundColor: "#ffffffff"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                text: "Docker 日志"
                                color: ThemeSystem.Theme.textPrimary
                                font.pixelSize: 20
                                font.bold: true
                                font.family: ThemeSystem.Theme.fontFamily
                                Layout.fillWidth: true
                            }

                            SpinBox {
                                from: 20
                                to: 500
                                value: settingsViewModel.dockerLogLines
                                onValueModified: settingsViewModel.setDockerLogLines(value)
                            }
                        }

                        TextArea {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: settingsViewModel.dockerLogs
                            readOnly: true
                            wrapMode: TextArea.NoWrap
                            font.family: "Consolas"
                            background: Rectangle {
                                radius: ThemeSystem.Theme.radiusMedium
                                color: "#0f172a"
                                border.width: 1
                                border.color: "#1e293b"
                            }
                            color: "#e2e8f0"
                        }

                        RowLayout {
                            spacing: 12

                            Button {
                                text: "刷新日志"
                                onClicked: settingsViewModel.loadDockerLogs()
                            }

                            Button {
                                text: "清空显示"
                                onClicked: settingsViewModel.clearDockerLogs()
                            }
                        }
                    }
                }
            }
        }
    }

    Component {
        id: appLogsManagementTab

        ColumnLayout {
            width: root.width
            spacing: ThemeSystem.Theme.sectionSpacing

            GlassCard {
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 14

                    Text {
                        text: "系统日志"
                        color: ThemeSystem.Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                        font.family: ThemeSystem.Theme.fontFamily
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        ComboBox {
                            Layout.preferredWidth: 240
                            model: settingsViewModel.logFilesModel
                            textRole: "name"
                            onActivated: function(index) {
                                var item = settingsViewModel.logFilesModel.get(index)
                                settingsViewModel.setSelectedLogFile(item.name || "")
                                settingsViewModel.loadAppLogs()
                            }
                        }

                        ComboBox {
                            Layout.preferredWidth: 160
                            model: ["", "ERROR", "WARNING", "INFO", "DEBUG"]
                            onActivated: function(index) {
                                settingsViewModel.setLogLevel(model[index])
                                settingsViewModel.loadAppLogs()
                            }
                        }

                        AppTextField {
                            Layout.fillWidth: true
                            text: settingsViewModel.logKeyword
                            placeholderText: "关键词搜索"
                            onTextEdited: settingsViewModel.setLogKeyword(text)
                            onAccepted: settingsViewModel.loadAppLogs()
                        }

                        SpinBox {
                            from: 50
                            to: 1000
                            stepSize: 50
                            value: settingsViewModel.logTailCount
                            onValueModified: settingsViewModel.setLogTailCount(value)
                        }
                    }

                    RowLayout {
                        spacing: 12

                        PrimaryButton {
                            text: "刷新日志"
                            onClicked: settingsViewModel.loadAppLogs()
                        }

                        Button {
                            text: "下载当前日志"
                            onClicked: settingsViewModel.downloadSelectedLogFile()
                        }

                        Button {
                            text: "清空显示"
                            onClicked: settingsViewModel.clearAppLogDisplay()
                        }

                        Text {
                            text: settingsViewModel.appLogSummary
                            color: ThemeSystem.Theme.textSecondary
                            font.family: ThemeSystem.Theme.fontFamily
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }

                    TextArea {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 520
                        text: settingsViewModel.appLogText
                        readOnly: true
                        wrapMode: TextArea.NoWrap
                        font.family: "Consolas"
                        background: Rectangle {
                            radius: ThemeSystem.Theme.radiusMedium
                            color: "#0f172a"
                            border.width: 1
                            border.color: "#1e293b"
                        }
                        color: "#e2e8f0"
                    }
                }
            }
        }
    }

    Component {
        id: textField

        AppTextField {
            Layout.fillWidth: true
            text: parent.fieldValue === undefined || parent.fieldValue === null ? "" : String(parent.fieldValue)
            onTextEdited: settingsViewModel.setServerField(root.serverCategory, parent.fieldKey, text)
        }
    }

    Component {
        id: passwordField

        AppTextField {
            Layout.fillWidth: true
            text: parent.fieldValue === undefined || parent.fieldValue === null ? "" : String(parent.fieldValue)
            echoMode: TextInput.Password
            onTextEdited: settingsViewModel.setServerField(root.serverCategory, parent.fieldKey, text)
        }
    }

    Component {
        id: multilineField

        TextArea {
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            text: parent.fieldValue === undefined || parent.fieldValue === null ? "" : String(parent.fieldValue)
            wrapMode: TextArea.Wrap
            onTextChanged: if (activeFocus) settingsViewModel.setServerField(root.serverCategory, parent.fieldKey, text)
            background: Rectangle {
                radius: ThemeSystem.Theme.radiusMedium
                color: "#f8fafc"
                border.width: 1
                border.color: ThemeSystem.Theme.lineColor
            }
            color: ThemeSystem.Theme.textPrimary
            selectionColor: ThemeSystem.Theme.colorPrimary
        }
    }

    Component {
        id: intField

        SpinBox {
            from: -2147483647
            to: 2147483647
            value: Number(parent.fieldValue || 0)
            onValueModified: settingsViewModel.setServerField(root.serverCategory, parent.fieldKey, value)
        }
    }

    Component {
        id: boolField

        RowLayout {
            Switch {
                checked: Boolean(parent.fieldValue)
                onToggled: settingsViewModel.setServerField(root.serverCategory, parent.fieldKey, checked)
            }

            Text {
                text: Boolean(parent.fieldValue) ? "已启用" : "未启用"
                color: ThemeSystem.Theme.textSecondary
                font.family: ThemeSystem.Theme.fontFamily
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }
}
