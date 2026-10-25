import "@testing-library/jest-dom/vitest";

Object.defineProperty(window, "scrollTo", {
  writable: true,
  value: () => {},
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});

// Node 22+ ships an experimental global `localStorage` that is undefined unless Node runs with
// --localstorage-file; it shadows jsdom's storage. Give the tests a working in-memory Storage.
if (typeof globalThis.localStorage?.getItem !== "function") {
  const store = new Map<string, string>();
  const memory: Storage = {
    get length() { return store.size; },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => { store.delete(key); },
    setItem: (key, value) => { store.set(key, String(value)); },
  };
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: memory });
  Object.defineProperty(window, "localStorage", { configurable: true, value: memory });
}
