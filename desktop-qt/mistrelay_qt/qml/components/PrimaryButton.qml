import QtQuick
import QtQuick.Controls
import "../theme" as ThemeSystem

Button {
    id: root

    implicitHeight: ThemeSystem.Theme.controlHeight
    implicitWidth: 140

    font.family: ThemeSystem.Theme.fontFamily
    font.pixelSize: 15
    font.bold: true

    contentItem: Text {
        text: root.text
        font: root.font
        color: "#ffffff"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: ThemeSystem.Theme.radiusMedium
        gradient: Gradient {
            GradientStop { position: 0.0; color: ThemeSystem.Theme.colorPrimary }
            GradientStop { position: 1.0; color: "#764ba2" }
        }
        opacity: root.enabled ? 1.0 : 0.55
        scale: root.down ? 0.985 : 1.0

        Behavior on scale {
            NumberAnimation { duration: 120 }
        }
    }
}
