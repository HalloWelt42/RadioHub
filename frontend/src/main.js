import { mount } from 'svelte';
import Zugang from './components/Zugang.svelte';

// Font Awesome (solid + brands + base)
import '@fortawesome/fontawesome-free/css/fontawesome.min.css';
import '@fortawesome/fontawesome-free/css/solid.min.css';
import '@fortawesome/fontawesome-free/css/brands.min.css';

// HiFi UI Framework CSS
import './styles/fonts.css';
import './styles/hifi-variables.css';
import './styles/hifi-base.css';
import './styles/hifi-components.css';

// erst die Anmeldung (Konto der Kellerwolke), dann die App
const app = mount(Zugang, {
  target: document.getElementById('app')
});

export default app;
