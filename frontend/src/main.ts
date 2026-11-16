import { mount } from "svelte";
import Zugang from "./components/Zugang.svelte";

// Gestaltung des Appkerns (Schriften, Symbole, Marken, Schale), dann das HiFi-CSS der alten Bereiche
import "appkern-oberflaeche/stil.css";
import "./styles/fonts.css";
import "./styles/hifi-variables.css";
import "./styles/hifi-base.css";
import "./styles/hifi-components.css";

// erst die Anmeldung (Konto der Kellerwolke), dann die App
mount(Zugang, { target: document.getElementById("app")! });
