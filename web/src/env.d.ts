/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SERVER_BASE_URL?: string
  readonly VITE_USE_HASH_ROUTER?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  __TAURI_INTERNALS__?: unknown
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
