"""Authentication and account interfaces for the platform."""

from __future__ import annotations

from .theme import icon, page

CSS = """
.auth-shell{min-height:calc(100vh - 190px);display:grid;place-items:center;padding:var(--space-7) 0}.auth-card{width:min(460px,100%);padding:var(--space-6)}
.auth-card h1{font-size:34px;margin-bottom:var(--space-3)}.auth-card>.muted{margin-bottom:var(--space-5)}
.auth-tabs{display:grid;grid-template-columns:1fr 1fr;background:var(--surface-2);padding:4px;border-radius:12px;margin-bottom:var(--space-5)}
.auth-tabs button{border:0;background:transparent;min-height:44px;border-radius:9px;cursor:pointer}.auth-tabs button.active{background:var(--surface);font-weight:700;box-shadow:var(--shadow)}
.form-field{display:grid;gap:6px;margin-bottom:var(--space-4)}.form-field label{font-weight:600;font-size:14px}.form-field input{min-height:46px;border:1px solid var(--line);border-radius:11px;background:var(--bg);padding:0 13px}
.auth-card .primary{width:100%}.form-error{display:none;color:var(--danger);background:var(--danger-bg);border:1px solid var(--danger-line);padding:var(--space-3);border-radius:10px;margin-bottom:var(--space-4)}.form-error.show{display:block}
.account-head{padding:var(--space-7) 0 var(--space-5);display:flex;justify-content:space-between;align-items:end;gap:var(--space-4)}.account-head h1{font-size:clamp(34px,5vw,50px);margin-bottom:var(--space-2)}
.account-grid{padding-bottom:var(--space-8)}.account-panel h2{font-size:22px;margin-bottom:var(--space-2)}
.panel-head{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);margin-bottom:var(--space-5)}.item-list{display:grid;gap:var(--space-2)}
.account-item{display:flex;justify-content:space-between;align-items:center;gap:var(--space-3);padding:var(--space-4);background:var(--surface-2);border:1px solid var(--line);border-radius:12px}.account-item p{margin:2px 0 0;color:var(--muted);font-size:13px}.account-item code{font-size:12px}
.empty-account{padding:var(--space-7) var(--space-4);text-align:center;border:1px dashed var(--line);border-radius:12px;color:var(--muted)}
.delete-project.danger{color:var(--danger);background:var(--danger-bg)}
.codes-liste{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:var(--space-2);margin:var(--space-4) 0}
.codes-liste code{font-size:14px;padding:11px 13px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;text-align:center;user-select:all}
.codes-avis{border-left:3px solid var(--brand);padding-left:var(--space-4);color:var(--ink);margin-bottom:var(--space-3)}
.codes-manquants{color:var(--danger)}
.auth-tabs.trois{grid-template-columns:1fr 1fr 1fr}
.auth-tabs button{font-size:14px;padding:0 6px}
.form-succes{display:none;border-left:3px solid var(--brand);padding-left:var(--space-4);margin-bottom:var(--space-4);color:var(--ink)}.form-succes.show{display:block}
.form-field.masque{display:none}
.auth-secours{margin-top:var(--space-4);color:var(--muted);font-size:13px;max-width:52ch}
.zone-rouge{margin-top:var(--space-5);border:1px solid var(--danger-line);background:var(--danger-bg);border-radius:var(--radius);padding:var(--space-5)}
.zone-rouge h2{font-size:19px;margin-bottom:var(--space-2)}.zone-rouge p{color:var(--muted);margin-bottom:var(--space-4);max-width:62ch}
.zone-rouge form{display:none;gap:var(--space-2);align-items:end;flex-wrap:wrap}.zone-rouge form.show{display:flex}
.zone-rouge input{min-height:44px;border:1px solid var(--danger-line);border-radius:10px;background:var(--surface);padding:0 12px;color:var(--ink)}
.zone-rouge .danger{min-height:44px;color:var(--danger);background:transparent;border:1px solid var(--danger-line);border-radius:10px;padding:0 16px;cursor:pointer;font-weight:600}
@media(max-width:780px){.account-head{align-items:start;flex-direction:column}}
"""

AUTH_BODY = f"""
<section class="shell auth-shell"><div class="card auth-card"><h1 id="auth-title">Se connecter</h1><p class="muted" id="auth-help">Retrouvez vos projets et poursuivez vos compilations.</p>
<div class="auth-tabs trois"><button class="active" type="button" data-mode="login">Connexion</button><button type="button" data-mode="register">Créer un compte</button><button type="button" data-mode="recover">Mot de passe oublié</button></div>
<div class="form-error" id="auth-error" role="alert"></div>
<div class="form-succes" id="auth-succes" role="status"></div><form id="auth-form" novalidate>
<div class="form-field"><label for="email">Adresse email</label><input id="email" type="email" autocomplete="email" required></div>
<div class="form-field masque" id="champ-code"><label for="code">Code de secours</label><input id="code" type="text" autocomplete="one-time-code" spellcheck="false"><small class="muted">L’un des huit codes remis à la création de votre compte. Chaque code ne sert qu’une fois.</small></div>
<div class="form-field"><label for="password" id="password-label">Mot de passe</label><input id="password" type="password" autocomplete="current-password" minlength="10" required><small class="muted">10 caractères au minimum.</small></div>
<button class="primary" type="submit">{icon('user')} <span id="submit-label">Se connecter</span></button></form>
<p class="auth-secours" id="auth-secours" hidden>Vos codes ont été affichés une seule fois, à la création du compte. Sans code, personne ne peut rouvrir votre compte à votre place : Monl n’envoie aucun courriel et ne conserve pas de quoi vous identifier autrement. Écrivez à l’exploitant du service, qui seul dispose d’un accès d’administration.</p></div></section>
"""

AUTH_SCRIPT = """
<script>
let mode='login';const form=document.querySelector('#auth-form'),error=document.querySelector('#auth-error');
const succes=document.querySelector('#auth-succes'),champCode=document.querySelector('#champ-code');
const aide=document.querySelector('#auth-secours');
/* Un tableau par mode plutôt que des ternaires empilés : à trois modes, la
   forme « login ? a : b » cesse de dire la vérité sans qu'on le voie. */
const MODES={
 login:{titre:'Se connecter',bouton:'Se connecter',
  intro:'Retrouvez vos projets et poursuivez vos compilations.',
  motdepasse:'Mot de passe',autocomplete:'current-password'},
 register:{titre:'Créer votre compte',bouton:'Créer le compte',
  intro:'Vos huit codes de secours vous seront remis une seule fois, juste après.',
  motdepasse:'Mot de passe',autocomplete:'new-password'},
 recover:{titre:'Retrouver votre compte',bouton:'Changer le mot de passe',
  intro:'Entrez un de vos codes de secours et choisissez un nouveau mot de passe.',
  motdepasse:'Nouveau mot de passe',autocomplete:'new-password'}};
function basculer(nouveau){mode=nouveau;const conf=MODES[mode];
 document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x.dataset.mode===mode));
 document.querySelector('#auth-title').textContent=conf.titre;
 document.querySelector('#auth-help').textContent=conf.intro;
 document.querySelector('#submit-label').textContent=conf.bouton;
 document.querySelector('#password-label').textContent=conf.motdepasse;
 document.querySelector('#password').autocomplete=conf.autocomplete;
 champCode.classList.toggle('masque',mode!=='recover');
 /* `required` doit suivre l'AFFICHAGE : un champ obligatoire mais masqué fait
    échouer la validation sur un champ que personne ne peut ni voir ni
    atteindre, et le bouton semble ne rien faire — le défaut que `novalidate`
    a déjà servi à réparer ici. */
 document.querySelector('#code').required=(mode==='recover');
 aide.hidden=(mode!=='recover');
 error.className='form-error';succes.className='form-succes';}
document.querySelectorAll('[data-mode]').forEach(button=>button.onclick=()=>basculer(button.dataset.mode));
form.onsubmit=async event=>{event.preventDefault();error.className='form-error';
 /* Le formulaire porte `novalidate` pour que CE code voie l'envoi. Sans lui,
    le navigateur bloquait tout seul sur une adresse sans « @ » : aucune
    requête ne partait, la bannière de la page restait VIDE, et le seul
    message était une bulle native — celle que la fenêtre d'un gestionnaire de
    mots de passe recouvre. Le bouton semblait ne rien faire. Le message n'est
    pas réécrit : on reprend celui du navigateur, déjà traduit. */
 const invalide=[...form.elements].find(champ=>champ.willValidate&&!champ.checkValidity());
 if(invalide){error.textContent=invalide.validationMessage;error.className='form-error show';invalide.focus();return;}
 const button=form.querySelector('button[type=submit]');button.disabled=true;
 const envoi={email:email.value,password:password.value};
 if(mode==='recover')envoi.code=document.querySelector('#code').value;
 try{const response=await fetch('/api/auth/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(envoi)});
 /* La récupération répond 204, SANS corps : demander son JSON lèverait sur le
    seul cas qui réussit, et la personne verrait une erreur après avoir brûlé
    un de ses huit codes. Le refus, lui, porte bien un détail. */
 if(!response.ok){let detail='Impossible de continuer.';
  try{detail=(await response.json()).detail||detail;}catch(_){}
  throw new Error(detail);}
 if(mode==='recover'){const adresse=email.value;basculer('login');email.value=adresse;
  document.querySelector('#code').value='';password.value='';
  succes.textContent='Mot de passe changé, et vos autres sessions ont été fermées. Connectez-vous avec le nouveau mot de passe.';
  succes.className='form-succes show';password.focus();return;}
 const next=new URLSearchParams(location.search).get('next');location.href=next&&next.startsWith('/')&&!next.startsWith('//')?next:'/console';
 }catch(e){error.textContent=e.message;error.className='form-error show';}finally{button.disabled=false;}};
</script>
"""

ACCOUNT_BODY = f"""
<section class="shell account-head"><div><h1>Vos projets.</h1><p class="muted" id="account-email"></p></div>
<button class="secondary" id="logout" type="button">Se déconnecter</button></section>
<section class="shell account-grid"><article class="card account-panel"><div class="panel-head"><div><h2>Projets compilés</h2><p class="muted">Conservés dans votre espace.</p></div><a class="primary" href="/console">{icon('compiler')} Nouveau projet</a></div><div class="item-list" id="projects"></div></article>
<article class="card account-panel" id="panneau-codes">
<div class="panel-head"><div><h2>Codes de secours</h2>
<p class="muted">Le seul moyen de reprendre la main si vous perdez votre mot de passe.</p></div>
<button class="secondary" id="regenerer-codes" type="button">Générer une nouvelle série</button></div>
<p class="muted" id="etat-codes">…</p>
<div id="codes-affiches"></div>
<div class="form-error" id="erreur-codes" role="alert"></div></article>
<article class="zone-rouge">
<h2>Supprimer votre compte</h2>
<p>Efface définitivement votre compte, vos clés d’accès, vos projets et les fichiers
compilés qui leur appartiennent. <b>Cette action est irréversible</b> — téléchargez
ce que vous voulez garder avant de continuer.</p>
<button class="danger" id="ouvrir-suppression" type="button">Supprimer mon compte</button>
<form id="suppression"><div class="form-field"><label for="mdp-suppression">Confirmez avec votre mot de passe</label>
<input id="mdp-suppression" type="password" autocomplete="current-password" required></div>
<button class="danger" type="submit">Supprimer définitivement</button>
<button class="ghost" id="annuler-suppression" type="button">Annuler</button></form>
<div class="form-error" id="erreur-suppression" role="alert"></div></article></section>
"""

ACCOUNT_SCRIPT = """
<script>
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function json(url,options){const r=await fetch(url,options);if(r.status===401){location.href='/login?next=/account';throw new Error('session');}const d=r.status===204?{}:await r.json();if(!r.ok)throw new Error(d.detail||'Erreur');return d;}
async function load(){const [me,projects]=await Promise.all([json('/api/auth/me'),json('/api/projects')]);
 document.querySelector('#account-email').textContent=me.email;document.querySelector('#projects').innerHTML=projects.projects.length?projects.projects.map(p=>`<div class="account-item"><div><b>${esc(p.name)}</b><p>Créé le ${new Date(p.created_at*1000).toLocaleDateString('fr-FR')} · expire le ${new Date(p.expires_at*1000).toLocaleDateString('fr-FR')}</p></div><span><a class="secondary" href="/api/projects/${encodeURIComponent(p.project_id)}/download">Télécharger</a><button class="ghost delete-project" data-id="${esc(p.project_id)}" type="button">Supprimer</button></span></div>`).join(''):'<div class="empty-account">Aucun projet. Compilez votre première spec.</div>';
 document.querySelectorAll('.delete-project').forEach(b=>b.onclick=async()=>{if(!b.dataset.confirmed){b.dataset.confirmed='1';b.textContent='Confirmer';b.classList.add('danger');return;}await json('/api/projects/'+b.dataset.id,{method:'DELETE'});load();});}
const etatCodes=document.querySelector('#etat-codes'),affiches=document.querySelector('#codes-affiches'),erreurCodes=document.querySelector('#erreur-codes');
async function chargerCodes(){try{const d=await json('/api/auth/recovery-codes');
 etatCodes.textContent=d.remaining?`${d.remaining} code${d.remaining>1?'s':''} encore utilisable${d.remaining>1?'s':''}. Ils ne sont pas relisibles : générer une nouvelle série remplace l'ancienne.`:"Aucun code utilisable. Sans mot de passe et sans code, ce compte serait définitivement inaccessible — générez une série maintenant.";
 etatCodes.className=d.remaining?'muted':'codes-manquants';}catch(e){etatCodes.textContent='';}}
document.querySelector('#regenerer-codes').onclick=async()=>{erreurCodes.className='form-error';
 try{const d=await json('/api/auth/recovery-codes',{method:'POST'});
  affiches.innerHTML='<p class="codes-avis"><b>Notez-les maintenant.</b> Ils ne seront plus jamais affichés, et l\\'ancienne série ne fonctionne plus. Chaque code ne sert qu\\'une fois.</p><div class="codes-liste">'+d.recovery_codes.map(c=>`<code>${esc(c)}</code>`).join('')+'</div>';
  chargerCodes();}catch(e){erreurCodes.textContent=e.message;erreurCodes.className='form-error show';}};
document.querySelector('#logout').onclick=async()=>{await fetch('/api/auth/logout',{method:'POST'});location.href='/';};
const zone=document.querySelector('#suppression'),erreur=document.querySelector('#erreur-suppression');
document.querySelector('#ouvrir-suppression').onclick=()=>{zone.classList.add('show');document.querySelector('#mdp-suppression').focus();};
document.querySelector('#annuler-suppression').onclick=()=>{zone.classList.remove('show');erreur.className='form-error';};
zone.onsubmit=async event=>{event.preventDefault();erreur.className='form-error';
 try{await json('/api/auth/account',{method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:document.querySelector('#mdp-suppression').value})});location.href='/';}
 catch(e){erreur.textContent=e.message;erreur.className='form-error show';}};
load();
</script>
"""

AUTH_HTML = page(title="Connexion — MONL", description="Accédez à votre espace Monl.",
                 body=AUTH_BODY, extra_css=CSS, scripts=AUTH_SCRIPT)
ACCOUNT_HTML = page(title="Votre compte — MONL", description="Vos projets compilés avec Monl.",
                    body=ACCOUNT_BODY, active="account", extra_css=CSS, scripts=ACCOUNT_SCRIPT)
