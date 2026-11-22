// Bauziel Webversion (RAD-4): Wurzel mit Radio und Podcasts (RAD-102), ohne Anmeldung. Die Wiedergabe läuft direkt im
// Browser (nur https-Ströme, ohne Zeitversatz und Aufnahme; Folgen direkt vom Server der Folge); gesetzt, bevor
// irgendetwas spielt.
import { wegSetzen } from "../../lib/playerEngine.js";
import { direkt } from "../../lib/wiedergabeweg.js";
import { folgenweg } from "./podcasts";

wegSetzen({ ...direkt, folgen: true, folge: folgenweg });

export { default as Wurzel } from "../../schale/WebWurzel.svelte";
