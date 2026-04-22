import QtQuick
import "../theme" as ThemeSystem

Rectangle {
    id: root

    default property alias contentData: contentRoot.data
    property int padding: ThemeSystem.Theme.cardPadding
    property color backgroundColor: ThemeSystem.Theme.glassBg
    property color borderColor: ThemeSystem.Theme.glassBorder

    radius: ThemeSystem.Theme.radiusLarge
    color: backgroundColor
    border.width: 1
    border.color: borderColor
    antialiasing: true

    Item {
        id: contentRoot
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
