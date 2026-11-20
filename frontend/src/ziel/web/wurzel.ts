// Bauziel Webversion (RAD-4): Wurzel nur mit Radio, ohne Anmeldung. Die Wiedergabe läuft direkt im Browser (nur
// https-Ströme, ohne Zeitversatz, Aufnahme und Folgen); gesetzt, bevor irgendetwas spielt.
import { wegSetzen } from "../../lib/playerEngine.js";
import { direkt } from "../../lib/wiedergabeweg.js";

wegSetzen(direkt);

export { default as Wurzel } from "../../schale/WebWurzel.svelte";
