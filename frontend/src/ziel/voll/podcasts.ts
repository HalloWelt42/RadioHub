// Bauziel volle App (RAD-17): Podcasts und Werbestellen über das eigene Backend.
import { api } from "../../lib/api.js";
import { BackendPodcastquelle } from "../../lib/podcasts/backend";
import { BackendWerbequelle, type Werbequelle } from "../../lib/podcasts/werbung";
import type { Podcastquelle } from "../../lib/podcasts/quelle";

export const podcastquelle: Podcastquelle = new BackendPodcastquelle(api);
export const werbequelle: Werbequelle = new BackendWerbequelle(api.baseUrl);
