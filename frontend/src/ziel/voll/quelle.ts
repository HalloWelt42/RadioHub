// Bauziel volle App: die Senderquelle gegen das eigene Backend. Die Favoriten der übrigen App (Telefon, alte Bereiche)
// laden nach jeder Änderung neu.
import { actions } from "../../lib/store.svelte.js";
import { BackendQuelle } from "../../lib/radio/backend";
import type { Senderquelle } from "../../lib/radio/quelle";

export const senderquelle: Senderquelle = new BackendQuelle({ beiFavoriten: () => void actions.loadFavorites() });
