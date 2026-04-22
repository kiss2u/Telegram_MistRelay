import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "theme" as ThemeSystem
import "components"
import "pages"

ApplicationWindow {
    id: window

    visible: true
    title: appViewModel.windowTitle
    color: ThemeSystem.Theme.surface

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#f7f9fd" }
            GradientStop { position: 1.0; color: "#eef4ff" }
        }
    }

    Loader {
        anchors.fill: parent
        sourceComponent: appViewModel.loggedIn ? shellComponent : loginComponent
    }

    Component {
        id: loginComponent

        LoginPage { }
    }

    Component {
        id: shellComponent

        AppShell { }
    }

    FloatingToast {
        id: toast
        z: 10
    }

    Connections {
        target: appViewModel

        function onToastRequested(level, message) {
            toast.showMessage(level, message)
        }
    }
}
