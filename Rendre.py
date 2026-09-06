"""Rendu HTML de la note. Un seul fichier autonome, deux modes de lecture."""

import html
import json
from datetime import datetime

MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]


def e(x):
    return html.escape(str(x if x is not None else ""))


def date_longue(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
        return f"{d.day} {MOIS[d.month - 1]} {d.year}"
    except ValueError:
        return iso


CSS = """
:root{
  --encre:#101720; --panneau:#18202B; --creux:#0B1119;
  --papier:#E9E5DC; --gris:#8D97A4; --trait:#26303D;
  --laiton:#C99A4B; --ecart:#C4614A; --tenu:#5E9B7E;
  --serif:"Newsreader",Georgia,serif; --sans:"Inter",system-ui,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--encre);color:var(--papier);
  font-family:var(--sans);font-size:16px;line-height:1.65;
  -webkit-font-smoothing:antialiased}
main{max-width:38rem;margin:0 auto;padding:1.5rem 1.25rem 5rem}
a{color:inherit;text-decoration:none;border-bottom:1px solid var(--trait)}
a:hover{border-color:var(--laiton)}
:focus-visible{outline:2px solid var(--laiton);outline-offset:3px}

.tete{display:flex;justify-content:space-between;align-items:baseline;
  gap:1rem;padding-bottom:.75rem;border-bottom:1px solid var(--trait)}
.tete h1{font-family:var(--serif);font-size:1.05rem;font-weight:500;margin:0;
  letter-spacing:.01em}
.tete span{color:var(--gris);font-size:.75rem;font-variant-numeric:tabular-nums}

.suivi{display:flex;flex-wrap:wrap;gap:.35rem;margin:.9rem 0 0}
.suivi b{font-weight:400;font-size:.72rem;color:var(--gris);
  border:1px solid var(--trait);border-radius:2px;padding:.15rem .45rem}

section{margin-top:2.75rem}
.etiquette{color:var(--laiton);font-size:.78rem;letter-spacing:.03em;
  margin:0 0 .6rem;font-weight:500}
h2{font-family:var(--serif);font-weight:400;font-size:1.5rem;line-height:1.3;
  margin:0 0 .75rem}
h3{font-family:var(--serif);font-weight:500;font-size:1.1rem;margin:0 0 .35rem}

.ouverture{font-family:var(--serif);font-size:1.55rem;line-height:1.35;
  margin:1.75rem 0 0;font-weight:400}

.bloc{border-left:2px solid var(--trait);padding:.1rem 0 .1rem 1rem;margin:1.1rem 0}
.bloc.vide{color:var(--gris);font-style:italic;border-left-color:var(--creux)}
.inexplique .bloc{border-left-color:var(--laiton)}
.divergence .bloc{border-left-color:var(--ecart)}
.bloc p{margin:.3rem 0}
.legende{color:var(--gris);font-size:.82rem}
.legende b{color:var(--papier);font-weight:500}

.synthese{list-style:none;padding:0;margin:0;font-family:var(--serif);
  font-size:1.12rem;line-height:1.55}
.synthese li{padding:.5rem 0;border-bottom:1px solid var(--trait)}
.synthese li:last-child{border-bottom:0}

table{width:100%;border-collapse:collapse;font-size:.85rem;
  font-variant-numeric:tabular-nums}
th{text-align:right;font-weight:500;color:var(--gris);font-size:.75rem;
  padding:.35rem .3rem;border-bottom:1px solid var(--trait)}
th:first-child{text-align:left}
td{padding:.42rem .3rem;text-align:right;border-bottom:1px solid var(--creux)}
td:first-child{text-align:left;color:var(--gris)}
tr.anormal td{color:var(--laiton)}
tr.anormal td:first-child{color:var(--laiton)}

details{border-top:1px solid var(--trait);padding:.85rem 0}
details[open]{padding-bottom:1.4rem}
summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;
  align-items:baseline;gap:1rem;font-family:var(--serif);font-size:1.15rem}
summary::-webkit-details-marker{display:none}
summary em{font-style:normal;color:var(--gris);font-size:.72rem;
  font-family:var(--sans);font-variant-numeric:tabular-nums;white-space:nowrap}

.chaine{list-style:none;counter-reset:c;padding:0;margin:.6rem 0 0}
.chaine li{counter-increment:c;position:relative;padding-left:1.6rem;margin:.3rem 0;
  font-size:.92rem}
.chaine li::before{content:counter(c);position:absolute;left:0;top:.05rem;
  color:var(--laiton);font-size:.72rem;font-variant-numeric:tabular-nums}
.chaine b{font-weight:500}
.chaine span{color:var(--gris)}

.faux{color:var(--gris);font-size:.88rem;margin:.55rem 0 0;
  border-left:2px solid var(--ecart);padding-left:.7rem}

.hypo{border-top:1px solid var(--creux);padding:.7rem 0}
.hypo p{margin:.15rem 0}
.hypo .meta{color:var(--gris);font-size:.76rem;font-variant-numeric:tabular-nums}
.verifiee .meta b{color:var(--tenu)}
.infirmee .meta b{color:var(--ecart)}

.score{display:flex;gap:1.5rem;flex-wrap:wrap;margin:.5rem 0 1rem}
.score div span{display:block;color:var(--gris);font-size:.74rem}
.score div b{font-family:var(--serif);font-size:1.6rem;font-weight:400;
  font-variant-numeric:tabular-nums}

footer{margin-top:4rem;padding-top:1rem;border-top:1px solid var(--trait);
  color:var(--gris);font-size:.76rem}

.bascule{position:sticky;top:0;z-index:5;display:flex;justify-content:flex-end;
  padding:.4rem 0;background:var(--encre)}
.bascule button{background:none;border:1px solid var(--trait);color:var(--gris);
  border-radius:2px;padding:.25rem .6rem;font:inherit;font-size:.74rem;cursor:pointer}
.bascule button:hover{color:var(--laiton);border-color:var(--laiton)}

body.diapo main{max-width:44rem}
body.diapo section,body.diapo .depart{display:none}
body.diapo section.vue,body.diapo .depart.vue{display:block;min-height:78vh;
  padding-top:1.5rem;animation:none}
body.diapo .bascule::before{content:attr(data-pos);color:var(--gris);
  font-size:.74rem;margin-right:auto;font-variant-numeric:tabular-nums}
body.diapo details{border:0}
body.diapo details summary{pointer-events:none}

@media (min-width:40rem){main{padding:2.5rem 2rem 6rem}
  .ouverture{font-size:1.9rem}h2{font-size:1.7rem}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media print{body{background:#fff;color:#000}.bascule{display:none}}
"""

JS = """
const corps=document.body, bar=document.querySelector('.bascule'),
      bouton=bar.querySelector('button'),
      vues=[...document.querySelectorAll('.depart, main > section')];
let i=0, diapo=false;

function montrer(n){
  i=Math.max(0,Math.min(vues.length-1,n));
  vues.forEach((v,k)=>v.classList.toggle('vue',k===i));
  bar.dataset.pos=String(i+1).padStart(2,'0')+' / '+vues.length;
  window.scrollTo(0,0);
}
function basculer(){
  diapo=!diapo;
  corps.classList.toggle('diapo',diapo);
  bouton.textContent=diapo?'lecture continue':'mode diapo';
  if(diapo){document.querySelectorAll('details').forEach(d=>d.open=true);montrer(0);}
  else{vues.forEach(v=>v.classList.remove('vue'));bar.dataset.pos='';}
}
bouton.addEventListener('click',basculer);
addEventListener('keydown',ev=>{
  if(ev.target.matches('input,textarea'))return;
  if(ev.key==='d'){basculer();return;}
  if(!diapo)return;
  if(ev.key==='j'||ev.key==='ArrowRight')montrer(i+1);
  if(ev.key==='k'||ev.key==='ArrowLeft')montrer(i-1);
});
"""


def bloc_vide(texte):
    return f'<div class="bloc vide"><p>{e(texte)}</p></div>'


def rendre(n):
    d = n.get("date", "")
    out = []
    a = out.append

    a("<!doctype html><html lang=fr><head><meta charset=utf-8>")
    a('<meta name=viewport content="width=device-width,initial-scale=1">')
    a('<meta name=color-scheme content=dark>')
    a(f"<title>Note economique du {e(date_longue(d))}</title>")
    a('<link rel=preconnect href="https://fonts.googleapis.com">')
    a('<link rel=preconnect href="https://fonts.gstatic.com" crossorigin>')
    a('<link rel=stylesheet href="https://fonts.googleapis.com/css2?'
      'family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&'
      'family=Inter:wght@400;500&display=swap">')
    a(f"<style>{CSS}</style></head><body><main>")

    a('<div class="bascule"><button type=button>mode diapo</button></div>')

    # --- ouverture ---
    a('<div class="depart">')
    a('<div class="tete"><h1>Note economique</h1>'
      f'<span>{e(date_longue(d))} &nbsp;{e(n.get("version", ""))}</span></div>')
    if n.get("exposition"):
        a('<div class="suivi">' + "".join(f"<b>{e(x)}</b>" for x in n["exposition"]) + "</div>")
    a(f'<p class="ouverture">{e(n.get("etat_du_jour", ""))}</p>')
    a("</div>")

    # --- inexplique : la section qui ouvre, volontairement ---
    a('<section class="inexplique"><p class="etiquette">Ce que la presse n\'explique pas</p>')
    a("<h2>Mouvements sans cause identifiee</h2>")
    if n.get("inexplique"):
        for x in n["inexplique"]:
            a('<div class="bloc">'
              f'<h3>{e(x.get("quoi"))}</h3>'
              f'<p>{e(x.get("ampleur"))}</p>'
              f'<p class="legende">Piste : {e(x.get("piste"))}</p>'
              f'<p class="legende">Manque : <b>{e(x.get("manque"))}</b></p></div>')
    else:
        a(bloc_vide("Aucun mouvement anormal aujourd'hui. Les prix suivent l'actualite."))
    a("</section>")

    # --- divergences ---
    a('<section class="divergence"><p class="etiquette">Presse contre prix</p>')
    a("<h2>Divergences</h2>")
    if n.get("divergences"):
        for x in n["divergences"]:
            a('<div class="bloc">'
              f'<h3>{e(x.get("constat"))}</h3>'
              f'<p class="legende">Presse : {e(x.get("presse"))}</p>'
              f'<p class="legende">Prix : {e(x.get("prix"))}</p>'
              f'<p>{e(x.get("lecture"))}</p></div>')
    else:
        a(bloc_vide("Le ton de la presse et le mouvement des prix concordent."))
    a("</section>")

    # --- synthese ---
    a('<section><p class="etiquette">Ce que les themes disent ensemble</p>')
    a("<h2>Synthese</h2>")
    if n.get("synthese"):
        a('<ul class="synthese">' + "".join(f"<li>{e(x)}</li>" for x in n["synthese"]) + "</ul>")
    else:
        a(bloc_vide("Pas de lien transversal aujourd'hui."))
    a("</section>")

    # --- marche ---
    if n.get("marche"):
        a('<section><p class="etiquette">Reference chiffree</p><h2>Marches</h2>')
        a("<table><thead><tr><th>Serie</th><th>Niveau</th><th>Var.</th><th>z</th>"
          "</tr></thead><tbody>")
        for m in n["marche"]:
            cls = ' class="anormal"' if m.get("anormal") else ""
            a(f'<tr{cls}><td>{e(m["nom"])}</td><td>{e(m["niveau"])}</td>'
              f'<td>{m["variation"]:+g}</td><td>{m["z"]:+g}</td></tr>')
        a("</tbody></table>")
        a('<p class="legende">z = ampleur de la variation du jour comparee aux 90 dernieres '
          "seances. Au-dela de 2, le mouvement sort de l'ordinaire.</p></section>")

    # --- themes ---
    a('<section><p class="etiquette">Le detail, si l\'ouverture t\'y renvoie</p>')
    a("<h2>Par theme</h2>")
    for t in n.get("themes", {}).values():
        retenus = t.get("retenus", [])
        a("<details><summary>" + e(t.get("titre", ""))
          + f'<em>{len(retenus)} retenus / {t.get("dossiers_bruts", 0)} dossiers</em></summary>')
        if not retenus:
            a(bloc_vide("Rien de materiel sur ce theme."))
        for r in retenus:
            a('<div class="bloc">')
            titre = e(r.get("titre"))
            a(f'<h3><a href="{e(r.get("url"))}">{titre}</a></h3>' if r.get("url")
              else f"<h3>{titre}</h3>")
            a(f'<p>{e(r.get("fait"))}</p>')
            marques = [f'{r.get("sources_independantes", "?")} sources independantes']
            if r.get("communique_interesse"):
                marques.append("communique d'une partie interessee")
            if r.get("materialite"):
                marques.append(f'materialite {e(r["materialite"])}')
            a(f'<p class="legende">{" &middot; ".join(map(e, marques))}</p>')
            if r.get("chaine"):
                a('<ul class="chaine">')
                for c in r["chaine"]:
                    a(f'<li><b>{e(c.get("canal"))}</b> <span>&rarr; {e(c.get("effet"))} '
                      f'&rarr; {e(c.get("actif"))}</span></li>')
                a("</ul>")
            if r.get("invalidation"):
                a(f'<p class="faux">Faux si : {e(r["invalidation"])}</p>')
            a("</div>")
        if t.get("ecarte_car_bruit"):
            a(f'<p class="legende">Ecarte comme bruit : '
              f'{e(", ".join(t["ecarte_car_bruit"][:6]))}</p>')
        a("</details>")
    a("</section>")

    # --- carnet ---
    a('<section><p class="etiquette">Ce que l\'outil avait annonce</p><h2>Carnet</h2>')
    fi = n.get("fiabilite", {})
    if fi:
        a('<div class="score">')
        for version, v in sorted(fi.items()):
            taux = f'{v["taux"]}%' if v["taux"] is not None else "&mdash;"
            a(f'<div><span>consignes {e(version)} &middot; {v["total"]} arbitrees</span>'
              f"<b>{taux}</b></div>")
        a("</div>")
    else:
        a('<p class="legende">Aucune hypothese encore arbitree. Le score apparait '
          "quand les premiers horizons sont atteints.</p>")

    carnet = n.get("carnet", [])
    recentes = [h for h in carnet if h["statut"] == "ouverte"][-6:]
    tranchees = [h for h in carnet if h["statut"] != "ouverte"][-5:]
    for h in reversed(recentes + tranchees):
        a(f'<div class="hypo {e(h["statut"])}">')
        a(f'<p>{e(h.get("enonce"))}</p>')
        bits = [e(h.get("date")), e(h.get("theme"))]
        if h.get("probabilite") is not None:
            bits.append(f'{round(float(h["probabilite"]) * 100)}%')
        if h.get("horizon_jours"):
            bits.append(f'{e(h["horizon_jours"])} j')
        bits.append(f'<b>{e(h["statut"])}</b>')
        a(f'<p class="meta">{" &middot; ".join(bits)}</p>')
        if h.get("preuve"):
            a(f'<p class="legende">{e(h["preuve"])}</p>')
        a("</div>")
    a("</section>")

    # --- contre-analyse ---
    a('<section><p class="etiquette">Contre les conclusions ci-dessus</p>')
    a("<h2>Ce qui rendrait cette note fausse</h2>")
    if n.get("contre_analyse"):
        for x in n["contre_analyse"]:
            a(f'<div class="bloc"><p>{e(x)}</p></div>')
    else:
        a(bloc_vide("Contre-analyse non produite."))
    a("</section>")

    nb = sum(t.get("articles_bruts", 0) for t in n.get("themes", {}).values())
    a(f"<footer><p>{nb} articles collectes, regroupes par dossier. "
      "Sources : GDELT, flux publics des institutions, series FRED. "
      f"Consignes {e(n.get('version'))} &mdash; le score de fiabilite ne vaut que "
      "par version.</p><p>Touche d pour le mode diapo, j et k pour naviguer.</p></footer>")

    a(f"</main><script>{JS}</script></body></html>")
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    src = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2]).write_text(rendre(src), encoding="utf-8")
