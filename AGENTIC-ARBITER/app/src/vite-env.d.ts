/// <reference types="vite/client" />

/* `import x from "...?url"` yields the emitted asset URL as a string. Declared so the
   maplibre worker import in SiteMap.tsx typechecks. */
declare module '*?url' {
  const url: string
  export default url
}
