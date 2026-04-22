import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../theme" as ThemeSystem

Button {
    id: root

    property bool active: false
    property string glyph: ""

    implicitHeight: 52
    leftPadding: 18
    rightPadding: 18

    background: Rectangle {
        radius: ThemeSystem.Theme.radiusMedium
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.active ? ThemeSystem.Theme.colorPrimary : "transparent" }
            GradientStop { position: 1.0; color: root.active ? "#764ba2" : "transparent" }
        }
        border.width: root.hovered && !root.active ? 1 : 0
        border.color: root.hovered && !root.active ? "#1fffffff" : "transparent"
    }

    contentItem: RowLayout {
        spacing: 12

        Text {
            text: root.glyph
            color: "#ffffff"
            font.pixelSize: 16
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            text: root.text
            color: "#ffffff"
            font.pixelSize: 15
            font.bold: root.active
            font.family: ThemeSystem.Theme.fontFamily
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
        }
    }
}
