// shares one look across every search field in the app
export const SEARCH_ICON_CLASS =
  'text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2'

// the browser draws its own cross on a search input, in a colour that is not ours,
// so it is hidden and every field carries the clear button below instead
export const SEARCH_INPUT_CLASS =
  'border-input bg-background text-foreground placeholder:text-muted-foreground focus:ring-primary w-full rounded-xl border py-2.5 pr-9 pl-9 text-sm focus:ring-2 focus:outline-none [&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-decoration]:appearance-none'

export const SEARCH_CLEAR_CLASS =
  'text-muted-foreground hover:text-foreground absolute top-1/2 right-3 -translate-y-1/2'
