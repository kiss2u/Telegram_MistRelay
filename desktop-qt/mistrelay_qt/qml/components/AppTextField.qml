import QtQuick
import QtQuick.Controls
import "../theme" as ThemeSystem

TextField {
    id: root

    implicitHeight: ThemeSystem.Theme.controlHeight
    color: ThemeSystem.Theme.textPrimary
    selectionColor: ThemeSystem.Theme.colorPrimary
    selectedTextColor: "#ffffff"
    font.family: ThemeSystem.Theme.fontFamily
    font.pixelSize: 15
    placeholderTextColor: ThemeSystem.Theme.textTertiary
    leftPadding: 16
    rightPadding: 16

    background: Rectangle {
        radius: ThemeSystem.Theme.radiusMedium
        color: "#f8fafc"
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus ? ThemeSystem.Theme.colorPrimary : ThemeSystem.Theme.lineColor
    }
}
