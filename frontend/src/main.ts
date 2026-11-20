import { mount } from "svelte";
// Wurzel je Bauziel ($ziel/wurzel): volle App mit Anmeldung oder Webversion nur mit Radio (RAD-4)
import { Wurzel } from "$ziel/wurzel";

// Gestaltung in Schichten (Entscheidung 24): Schriften, Symbole, Marken und Schale des Appkerns, seine Instrumente und
// Vorlagen in allen Breiten (auch am Telefon), dann die Marken des Radios mit seiner Vorlage, Bausteine und Anordnung.
import "appkern-oberflaeche/stil.css";
import "appkern-oberflaeche/instrumente.css";
import "appkern-oberflaeche/vorlagen-alle-breiten.css";
import "appkern-oberflaeche/instrumente";
import "@fontsource/orbitron/900.css";
import "./stil/radio-marken.css";
import "./stil/vorlagen/grund.css";
import "./stil/vorlagen/hifi.css";
import "./stil/bausteine.css";
import "./stil/radio.css";
import "./stil/einstellungen.css";
import "./stil/telefon.css";
import "./stil/kanzel.css";
import "./stil/rechner.css";
import "./stil/podcasts.css";
// Alte Bereiche bis zu ihrem Neubau (Etappen 3 und 6): ihre Variablen aus den Marken, dann ihr bisheriges CSS
import "./styles/bruecke.css";
import "./styles/hifi-base.css";
import "./styles/hifi-components.css";

mount(Wurzel, { target: document.getElementById("app")! });
