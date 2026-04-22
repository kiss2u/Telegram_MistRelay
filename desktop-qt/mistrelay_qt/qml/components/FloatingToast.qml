import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem

Item {
    id: root

    property string level: "info"
    property string message: ""
    property bool open: false

    function showMessage(nextLevel, nextMessage) {
        level = nextLevel
        message = nextMessage
        open = true
        hideTimer.restart()
    }

    anchors.top: parent.top
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.topMargin: 18
    width: Math.min(parent.width - 48, 560)
    height: banner.implicitHeight
    visible: open
    opacity: open ? 1 : 0

    Behavior on opacity {
        NumberAnimation { duration: 180 }
    }

    Rectangle {
        id: banner
        width: parent.width
        radius: ThemeSystem.Theme.radiusMedium
        color: level === "success"
               ? ThemeSystem.Theme.successSoft
               : level === "warning"
                 ? ThemeSystem.Theme.warningSoft
                 : level === "danger"
                   ? ThemeSystem.Theme.dangerSoft
                   : ThemeSystem.Theme.infoSoft
        border.width: 1
        border.color: level === "success"
                      ? "#86efac"
                      : level === "warning"
                        ? "#fcd34d"
                        : level === "danger"
                          ? "#fca5a5"
                          : "#93c5fd"

        implicitHeight: content.implicitHeight + 24

        RowLayout {
            id: content
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Text {
                text: level === "success" ? "成功" : level === "warning" ? "提醒" : level === "danger" ? "错误" : "信息"
                font.bold: true
                color: ThemeSystem.Theme.textPrimary
                font.family: ThemeSystem.Theme.fontFamily
            }

            Text {
                Layout.fillWidth: true
                text: root.message
                wrapMode: Text.WordWrap
                color: ThemeSystem.Theme.textPrimary
                font.family: ThemeSystem.Theme.fontFamily
            }
        }
    }

    Timer {
        id: hideTimer
        interval: 3200
        repeat: false
        onTriggered: root.open = false
    }
}
