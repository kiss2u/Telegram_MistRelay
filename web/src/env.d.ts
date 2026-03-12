/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SERVER_BASE_URL?: string
  readonly VITE_USE_HASH_ROUTER?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  __TAURI__?: {
    core?: {
      invoke<T = unknown>(command: string, args?: Record<string, unknown>): Promise<T>
      convertFileSrc?(filePath: string, protocol?: string): string
    }
  }
  __TAURI_INTERNALS__?: {
    convertFileSrc?(filePath: string, protocol?: string): string
  } | unknown
}

declare const __APP_VERSION__: string

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
