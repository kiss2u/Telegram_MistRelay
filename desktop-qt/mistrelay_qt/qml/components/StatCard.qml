import QtQuick
import QtQuick.Layouts
import "../theme" as ThemeSystem

GlassCard {
    id: root

    property string title: ""
    property string value: ""
    property string caption: ""
    property string tone: "primary"

    function toneColor() {
        switch (tone) {
        case "success":
            return ThemeSystem.Theme.colorSuccess
        case "warning":
            return ThemeSystem.Theme.colorWarning
        case "danger":
            return ThemeSystem.Theme.colorDanger
        case "info":
            return ThemeSystem.Theme.colorInfo
        default:
            return ThemeSystem.Theme.colorPrimary
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Rectangle {
            Layout.preferredWidth: 42
            Layout.preferredHeight: 6
            radius: 3
            color: root.toneColor()
        }

        Text {
            text: root.title
            color: ThemeSystem.Theme.textSecondary
            font.pixelSize: 14
            font.family: ThemeSystem.Theme.fontFamily
        }

        Text {
            text: root.value
            color: ThemeSystem.Theme.textPrimary
            font.pixelSize: 30
            font.bold: true
            font.family: ThemeSystem.Theme.fontFamily
        }

        Text {
            text: root.caption
            color: ThemeSystem.Theme.textTertiary
            font.pixelSize: 13
            wrapMode: Text.WordWrap
            font.family: ThemeSystem.Theme.fontFamily
        }
    }
}
