/**
 * Gesten in der Weckeransicht, rein rechnend: Wischen links oder rechts (Layout wechseln), Antippen, langer Druck.
 * Ein Wischen ist deutlich waagerecht und zügig; ein Antippen bleibt fast an der Stelle.
 */

export const WISCHEN_MIN_PX = 60;
export const WISCHEN_MAX_MS = 800;
export const STILL_PX = 12;
export const LANG_MS = 600;

/** start/ende: { x, y, t } -> 'links' | 'rechts' | 'tippen' | 'lang' | null */
export function geste(start, ende) {
  const dx = ende.x - start.x;
  const dy = ende.y - start.y;
  const dauer = ende.t - start.t;
  const weg = Math.hypot(dx, dy);
  if (Math.abs(dx) >= WISCHEN_MIN_PX && Math.abs(dx) > 1.5 * Math.abs(dy) && dauer <= WISCHEN_MAX_MS) {
    return dx < 0 ? 'links' : 'rechts';
  }
  if (weg <= STILL_PX) return dauer >= LANG_MS ? 'lang' : 'tippen';
  return null;
}
