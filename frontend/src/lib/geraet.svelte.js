/**
 * Welche Oberfläche gilt: eigene Telefonansicht unter 900 Pixeln Breite (die Rechneransicht braucht gemessen gut
 * 830), bei niedriger Höhe (Telefon quer) oder bei Fingerbedienung bis 1100 Pixel; quer und niedrig ist die
 * Weckeransicht. Die Rechneransicht bleibt sonst.
 */

const TELEFON = '(max-width: 899px), (max-height: 500px), (pointer: coarse) and (max-width: 1100px)';
const QUER = '(orientation: landscape) and (max-height: 500px)';

export const geraet = $state({ telefon: false, quer: false });

function binden(abfrage, feld) {
  const m = window.matchMedia(abfrage);
  geraet[feld] = m.matches;
  m.addEventListener('change', (e) => { geraet[feld] = e.matches; });
}

if (typeof window !== 'undefined' && window.matchMedia) {
  binden(TELEFON, 'telefon');
  binden(QUER, 'quer');
}
