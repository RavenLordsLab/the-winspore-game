import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Devin's Tank Game", layout="wide")
st.title("Devin's Tank Game")

game_html = r"""
<!DOCTYPE html>
<html>
<head>
<style>
  body { background:#111; margin:0; display:flex; flex-direction:column; align-items:center; font-family:monospace; }
  canvas { border:3px solid #0f0; image-rendering:pixelated; display:block; }
  #hud { color:#0f0; font-size:16px; margin:6px; display:none; }
  #gameover,#win { display:none; color:#f00; font-size:28px; text-align:center; margin:8px; }
  #win { color:#ff0; }
  .btn { background:#050; color:#0f0; border:2px solid #0f0; font-family:monospace;
         font-size:16px; padding:10px 20px; margin:6px; cursor:pointer; }
  .btn:hover { background:#0f0; color:#000; }
  .btn.sel { background:#0f0; color:#000; }
  #setup { color:#0f0; text-align:center; padding:10px; }
  #setup h1 { font-size:28px; margin:4px; }
  #setup h2 { font-size:18px; margin:8px; color:#0a0; }
  #slots { display:flex; flex-wrap:wrap; justify-content:center; gap:10px; margin:10px; }
  .slot { border:2px solid #0a0; padding:8px; min-width:130px; }
  .slot h3 { margin:4px; font-size:14px; color:#0f0; }
  #minimap { position:absolute; top:8px; right:8px; border:1px solid #0a0; }
</style>
</head>
<body>

<div id="setup">
  <h1>*** DEVIN'S TANK GAME ***</h1>
  <h2>HOW MANY IN YOUR SQUAD?</h2>
  <div>
    <button class="btn" id="sq1" onclick="setSquad(1)">1</button>
    <button class="btn" id="sq2" onclick="setSquad(2)">2</button>
    <button class="btn" id="sq3" onclick="setSquad(3)">3</button>
    <button class="btn" id="sq4" onclick="setSquad(4)">4</button>
    <button class="btn" id="sq5" onclick="setSquad(5)">5</button>
  </div>
  <div id="slotpanel" style="display:none">
    <h2>PICK YOUR VEHICLES</h2>
    <div id="slots"></div>
    <button class="btn" onclick="startGame()" style="font-size:20px;padding:14px 30px;margin-top:10px;">
      ▶ START GAME
    </button>
    <p style="font-size:12px;color:#080;">MOVE: Arrow Keys &nbsp;|&nbsp; SHOOT: Space &nbsp;|&nbsp; Huge open world — explore!</p>
  </div>
</div>

<div id="hud">
  SCORE: <span id="score">0</span> &nbsp;|&nbsp;
  LIVES: <span id="lives">3</span> &nbsp;|&nbsp;
  ENEMIES: <span id="enleft">100</span> &nbsp;|&nbsp;
  POS: <span id="pos">0,0</span>
</div>
<div style="position:relative;display:inline-block;">
  <canvas id="c" width="800" height="480" style="display:none"></canvas>
  <canvas id="mm" width="120" height="80" id="minimap" style="display:none;position:absolute;top:8px;right:8px;border:1px solid #0a0;"></canvas>
</div>
<div id="gameover"></div>
<div id="win"></div>

<script>
const CW=800, CH=480;
const WW=4000, WH=3000;  // Huge world

let squadSize=1;
let squadTypes=[];
let canvas,ctx,mmCanvas,mmCtx;
let squad, bullets, enemies, aliens, particles, stars;
let score=0, lives=3, frame=0, gameRunning=false, animId;
let cam={x:0,y:0};
const keys={};

// Formation offsets for squad members (relative to lead)
const FORMATIONS = [
  [[0,0]],
  [[0,-30],[0,30]],
  [[0,0],[-36,-36],[-36,36]],
  [[0,-22],[0,22],[-44,-44],[-44,44]],
  [[0,0],[-30,-36],[-30,36],[-64,-58],[-64,58]]
];

function setSquad(n){
  squadSize=n;
  ['sq1','sq2','sq3','sq4','sq5'].forEach((id,i)=>{
    document.getElementById(id).className = (i+1===n) ? 'btn sel' : 'btn';
  });
  document.getElementById('slotpanel').style.display='block';
  let slotsDiv = document.getElementById('slots');
  slotsDiv.innerHTML='';
  squadTypes = Array(n).fill('tank');
  for(let i=0;i<n;i++){
    let idx=i;
    slotsDiv.innerHTML += `
      <div class="slot">
        <h3>Vehicle ${i+1}</h3>
        <button class="btn sel" id="t${i}_tank" onclick="setType(${i},'tank')">🟢 TANK</button>
        <button class="btn" id="t${i}_plane" onclick="setType(${i},'plane')">🟢 PLANE</button>
        <button class="btn" id="t${i}_boat" onclick="setType(${i},'boat')">🟢 BOAT</button>
      </div>`;
  }
}

function setType(idx, type){
  squadTypes[idx]=type;
  ['tank','plane','boat'].forEach(t=>{
    let el=document.getElementById('t'+idx+'_'+t);
    if(el) el.className = (t===type)?'btn sel':'btn';
  });
}

function startGame(){
  document.getElementById('setup').style.display='none';
  document.getElementById('hud').style.display='block';
  canvas=document.getElementById('c'); canvas.style.display='block';
  mmCanvas=document.getElementById('mm'); mmCanvas.style.display='block';
  ctx=canvas.getContext('2d'); ctx.imageSmoothingEnabled=false;
  mmCtx=mmCanvas.getContext('2d');
  initGame();
  gameRunning=true;
  loop();
}

document.addEventListener('keydown',e=>{keys[e.code]=true;e.preventDefault();});
document.addEventListener('keyup',e=>{keys[e.code]=false;});

function initGame(){
  // Build squad — lead starts at world center-ish
  let lead = {wx:600, wy:WH/2};
  squad = [];
  let offsets = FORMATIONS[squadSize-1];
  for(let i=0;i<squadSize;i++){
    squad.push({
      type: squadTypes[i],
      wx: lead.wx + offsets[i][0],
      wy: lead.wy + offsets[i][1],
      w: squadTypes[i]==='boat'?72:squadTypes[i]==='plane'?64:60,
      h: squadTypes[i]==='boat'?40:squadTypes[i]==='plane'?28:36,
      shootCooldown:0,
      invincible:0
    });
  }

  // Stars (world-space, tiled)
  stars=Array.from({length:300},()=>({wx:Math.random()*WW,wy:Math.random()*WH,s:Math.random()*2+1}));

  bullets=[]; particles=[]; floaties=[];

  // 100 green enemy tanks spread through the world
  enemies=[];
  for(let i=0;i<100;i++){
    enemies.push({
      wx:800+Math.random()*(WW-1000), wy:200+Math.random()*(WH-400),
      w:48,h:28, alive:true,
      vx:(Math.random()-0.5)*1.2, vy:(Math.random()-0.5)*0.6,
      shootTimer:60+Math.floor(Math.random()*200)
    });
  }
  // 20 alien UFOs
  aliens=[];
  for(let i=0;i<20;i++){
    aliens.push({
      wx:500+Math.random()*(WW-600), wy:80+Math.random()*600,
      w:44,h:24, alive:true,
      vx:(Math.random()-0.5)*1.4, vy:0, waveOff:Math.random()*Math.PI*2,
      shootTimer:80+Math.floor(Math.random()*180)
    });
  }

  score=0; lives=10;
  updateHUD();
  camTo();
}

function camTo(){
  let lead=squad[0];
  cam.x = lead.wx - CW/2;
  cam.y = lead.wy - CH/2;
  cam.x = Math.max(0,Math.min(WW-CW, cam.x));
  cam.y = Math.max(0,Math.min(WH-CH, cam.y));
}

function updateHUD(){
  document.getElementById('score').textContent=score;
  document.getElementById('lives').textContent=lives;
  document.getElementById('enleft').textContent=enemies.filter(e=>e.alive).length+aliens.filter(a=>a.alive).length;
  document.getElementById('pos').textContent=Math.floor(squad[0].wx)+','+Math.floor(squad[0].wy);
}

let floaties=[];
function showFloaty(wx,wy,text,color){ floaties.push({wx,wy,text,color,life:50}); }

function spawnParticles(wx,wy,color,n){
  for(let i=0;i<n;i++){
    let a=Math.random()*Math.PI*2,sp=1+Math.random()*4;
    particles.push({wx,wy,vx:Math.cos(a)*sp,vy:Math.sin(a)*sp,life:20+Math.random()*20,color});
  }
}

function squadShoot(){
  for(let v of squad){
    if(v.shootCooldown>0) continue;
    let type=v.type;
    if(type==='boat'){
      for(let a=-3;a<=3;a++){
        let ang=a*0.15;
        bullets.push({wx:v.wx+v.w,wy:v.wy+v.h/2,vx:9*Math.cos(ang),vy:9*Math.sin(ang),owner:'player',r:4,color:'#ff0'});
      }
      v.shootCooldown=8;
    } else if(type==='plane'){
      bullets.push({wx:v.wx+v.w,wy:v.wy+8,vx:10,vy:-1,owner:'player',r:3,color:'#0ff'});
      bullets.push({wx:v.wx+v.w,wy:v.wy+v.h-8,vx:10,vy:1,owner:'player',r:3,color:'#0ff'});
      v.shootCooldown=12;
    } else {
      bullets.push({wx:v.wx+v.w,wy:v.wy+10,vx:11,vy:0,owner:'player',r:5,color:'#f80'});
      v.shootCooldown=20;
    }
  }
}

function enemyShoot(e,isAlien){
  let lead=squad[0];
  let dx=lead.wx-e.wx, dy=lead.wy-e.wy;
  let dist=Math.sqrt(dx*dx+dy*dy)||1;
  let sp=isAlien?5:3.5;
  bullets.push({wx:e.wx,wy:e.wy+e.h/2,vx:dx/dist*sp,vy:dy/dist*sp,owner:'enemy',r:3,color:isAlien?'#f0f':'#f44'});
}

function checkHit(bwx,bwy,br,ex,ey,ew,eh){
  return bwx+br>ex&&bwx-br<ex+ew&&bwy+br>ey&&bwy-br<ey+eh;
}

function respawn(){
  lives--;
  document.getElementById('lives').textContent=lives;
  if(lives<=0){ endGame(false); return false; }
  score+=25;
  // Snap squad back a bit
  for(let v of squad){
    v.wx=Math.max(100,v.wx-200);
    v.invincible=120;
  }
  bullets=bullets.filter(b=>b.owner==='player');
  return true;
}

function loop(){
  if(!gameRunning) return;
  frame++;
  update();
  draw();
  drawMinimap();
  animId=requestAnimationFrame(loop);
}

function update(){
  let spd=3.5;
  let dx=0,dy=0;
  if(keys['ArrowLeft']) dx=-spd;
  if(keys['ArrowRight']) dx=spd;
  if(keys['ArrowUp']) dy=-spd;
  if(keys['ArrowDown']) dy=spd;
  if(keys['Space']) squadShoot();

  let offsets=FORMATIONS[squadSize-1];

  // Move lead, then sync rest of squad in formation
  let lead=squad[0];
  lead.wx=Math.max(0,Math.min(WW-lead.w, lead.wx+dx));
  lead.wy=Math.max(0,Math.min(WH-lead.h, lead.wy+dy));
  for(let i=1;i<squad.length;i++){
    squad[i].wx = lead.wx + offsets[i][0];
    squad[i].wy = lead.wy + offsets[i][1];
    squad[i].wx=Math.max(0,Math.min(WW-squad[i].w, squad[i].wx));
    squad[i].wy=Math.max(0,Math.min(WH-squad[i].h, squad[i].wy));
  }

  for(let v of squad){ if(v.shootCooldown>0)v.shootCooldown--; if(v.invincible>0)v.invincible--; }

  camTo();

  // Move bullets
  for(let b of bullets){ b.wx+=b.vx; b.wy+=b.vy; }
  bullets=bullets.filter(b=>b.wx>-50&&b.wx<WW+50&&b.wy>-50&&b.wy<WH+50);

  // Move enemies — patrol and bounce off world edges
  for(let e of enemies){
    if(!e.alive) continue;
    e.wx+=e.vx; e.wy+=e.vy;
    if(e.wx<0||e.wx>WW-e.w) e.vx*=-1;
    if(e.wy<0||e.wy>WH-e.h) e.vy*=-1;
    e.shootTimer--;
    // Only shoot if near any squad member
    let near=squad.some(v=>Math.hypot(v.wx-e.wx,v.wy-e.wy)<500);
    if(e.shootTimer<=0){
      if(near) enemyShoot(e,false);
      e.shootTimer=80+Math.floor(Math.random()*160);
    }
  }

  // Move aliens — sine wave patrol
  for(let a of aliens){
    if(!a.alive) continue;
    a.wx+=a.vx; a.wy+=200+Math.sin(frame*0.03+a.waveOff)*120;
    // Bounce
    if(a.wx<0||a.wx>WW-a.w){ a.vx*=-1; a.wx=Math.max(0,Math.min(WW-a.w,a.wx)); }
    a.wy=Math.max(20,Math.min(WH*0.4,a.wy));
    a.shootTimer--;
    let near=squad.some(v=>Math.hypot(v.wx-a.wx,v.wy-a.wy)<600);
    if(a.shootTimer<=0){
      if(near) enemyShoot(a,true);
      a.shootTimer=60+Math.floor(Math.random()*140);
    }
  }

  // Bullet collisions
  for(let b of bullets){
    if(b.dead) continue;
    if(b.owner==='player'){
      for(let e of enemies){
        if(!e.alive||b.dead) continue;
        if(checkHit(b.wx,b.wy,b.r,e.wx,e.wy,e.w,e.h)){
          e.alive=false; b.dead=true;
          spawnParticles(e.wx+e.w/2,e.wy+e.h/2,'#0f0',12);
          score+=10; updateHUD(); break;
        }
      }
      for(let a of aliens){
        if(!a.alive||b.dead) continue;
        if(checkHit(b.wx,b.wy,b.r,a.wx,a.wy,a.w,a.h)){
          a.alive=false; b.dead=true;
          spawnParticles(a.wx+a.w/2,a.wy+a.h/2,'#f0f',16);
          score+=50; updateHUD(); break;
        }
      }
    } else {
      for(let v of squad){
        if(v.invincible||b.dead) continue;
        // Glancing hit: bullet within 2x radius of edge but not center
        let cx=v.wx+v.w/2, cy=v.wy+v.h/2;
        let dist=Math.hypot(b.wx-cx, b.wy-cy);
        let innerR = Math.min(v.w,v.h)*0.28;  // core hit zone
        let outerR = Math.min(v.w,v.h)*0.62;  // glance zone
        let directHit = checkHit(b.wx,b.wy,b.r,v.wx+v.w*0.2,v.wy+v.h*0.2,v.w*0.6,v.h*0.6);
        let glanceHit = !directHit && checkHit(b.wx,b.wy,b.r*2,v.wx,v.wy,v.w,v.h);
        if(directHit){
          b.dead=true;
          spawnParticles(v.wx+v.w/2,v.wy+v.h/2,'#f80',10);
          showFloaty(v.wx,v.wy,'DIRECT HIT!','#f44');
          if(!respawn()) return;
          updateHUD();
          break;
        } else if(glanceHit){
          b.dead=true;
          score+=15;
          spawnParticles(b.wx,b.wy,'#ff0',5);
          showFloaty(v.wx,v.wy,'DODGE! +15','#ff0');
          v.invincible=30;
          updateHUD();
          break;
        }
      }
    }
  }
  bullets=bullets.filter(b=>!b.dead);

  for(let p of particles){ p.wx+=p.vx; p.wy+=p.vy; p.life--; p.vy+=0.12; }
  particles=particles.filter(p=>p.life>0);
  for(let f of floaties){ f.wy-=0.8; f.life--; }
  floaties=floaties.filter(f=>f.life>0);

  let aliveCount=enemies.filter(e=>e.alive).length+aliens.filter(a=>a.alive).length;
  if(aliveCount===0){ endGame(true); return; }
}

// World-to-screen
function ws(wx,wy){ return {x:wx-cam.x, y:wy-cam.y}; }
function inView(wx,wy,w,h){ return wx-cam.x+w>0&&wx-cam.x<CW&&wy-cam.y+h>0&&wy-cam.y<CH; }

function draw(){
  ctx.fillStyle='#0a0a1a'; ctx.fillRect(0,0,CW,CH);

  // World background zones
  // Sky area (top 40% of world)
  let skyY = -cam.y; let skyH = WH*0.4-cam.y;
  ctx.fillStyle='#0a1a2a';
  ctx.fillRect(0,Math.max(0,skyY),CW,Math.min(CH,skyH));
  // Sea area (bottom 30%)
  let seaStart=(WH*0.7-cam.y);
  if(seaStart<CH){
    ctx.fillStyle='#001a3a';
    ctx.fillRect(0,Math.max(0,seaStart),CW,CH-Math.max(0,seaStart));
    // Waves
    ctx.strokeStyle='#0055aa'; ctx.lineWidth=2;
    for(let wx=0;wx<WW;wx+=60){
      let sx=wx-cam.x;
      if(sx<-60||sx>CW+60) continue;
      let sy=WH*0.7+8-cam.y+Math.sin(frame*0.04+wx*0.02)*4;
      ctx.beginPath(); ctx.moveTo(sx,sy); ctx.lineTo(sx+28,sy-6); ctx.stroke();
    }
  }
  // Ground (middle)
  let groundY=WH*0.4-cam.y, groundH=WH*0.3;
  ctx.fillStyle='#1a1200';
  ctx.fillRect(0,Math.max(0,groundY),CW,Math.min(groundH,CH-Math.max(0,groundY)));
  // Grass patches
  ctx.fillStyle='#0a2200';
  for(let gx=0;gx<WW;gx+=80){
    let sx=gx-cam.x;
    if(sx<-80||sx>CW) continue;
    let sy=WH*0.4-cam.y;
    if(sy<CH&&sy>-10) ctx.fillRect(sx,Math.max(0,sy),40,5);
  }

  // Stars
  for(let s of stars){
    let p=ws(s.wx,s.wy);
    if(p.y>WH*0.4-cam.y) continue;
    if(p.x<-2||p.x>CW+2||p.y<-2||p.y>CH+2) continue;
    ctx.fillStyle='#fff'; ctx.fillRect(p.x,p.y,s.s,s.s);
  }

  // Clouds
  ctx.fillStyle='#1a2a3a';
  for(let i=0;i<12;i++){
    let cx=((i*380+frame*0.3)%WW)-cam.x;
    let cy=(i*60+80)-cam.y;
    if(cx<-100||cx>CW||cy<-30||cy>WH*0.35-cam.y) continue;
    ctx.fillRect(cx,cy,100,22); ctx.fillRect(cx+20,cy-14,60,22);
  }

  // Enemies
  for(let e of enemies){
    if(!e.alive||!inView(e.wx,e.wy,e.w,e.h)) continue;
    let p=ws(e.wx,e.wy);
    drawTank(ctx,p.x,p.y,e.w,e.h,'#0a0','#060',true);
  }
  for(let a of aliens){
    if(!a.alive||!inView(a.wx,a.wy,a.w,a.h)) continue;
    let p=ws(a.wx,a.wy);
    drawUFO(ctx,p.x,p.y,a.w,a.h);
  }

  // Bullets
  for(let b of bullets){
    if(!inView(b.wx,b.wy,1,1)) continue;
    let p=ws(b.wx,b.wy);
    ctx.fillStyle=b.color;
    ctx.beginPath(); ctx.arc(p.x,p.y,b.r,0,Math.PI*2); ctx.fill();
    ctx.globalAlpha=0.3;
    ctx.beginPath(); ctx.arc(p.x,p.y,b.r*2.5,0,Math.PI*2); ctx.fill();
    ctx.globalAlpha=1;
  }

  // Squad (blink if invincible)
  for(let v of squad){
    if(v.invincible && frame%6<3) continue;
    let p=ws(v.wx,v.wy);
    if(v.type==='tank') drawTank(ctx,p.x,p.y,v.w,v.h,'#0f0','#080',false);
    else if(v.type==='plane') drawPlane(ctx,p.x,p.y,v.w,v.h);
    else drawBoat(ctx,p.x,p.y,v.w,v.h);
  }

  // Particles
  for(let p of particles){
    let sp=ws(p.wx,p.wy);
    if(sp.x<-4||sp.x>CW+4||sp.y<-4||sp.y>CH+4) continue;
    ctx.globalAlpha=p.life/40;
    ctx.fillStyle=p.color;
    ctx.fillRect(sp.x-2,sp.y-2,4,4);
  }
  ctx.globalAlpha=1;

  // Floaty text
  ctx.font='bold 14px monospace';
  for(let f of floaties){
    let sp=ws(f.wx,f.wy);
    ctx.globalAlpha=f.life/50;
    ctx.fillStyle=f.color;
    ctx.fillText(f.text, sp.x, sp.y);
  }
  ctx.globalAlpha=1;

  if(lives<=2&&frame%20<10){ ctx.fillStyle='rgba(255,0,0,0.07)'; ctx.fillRect(0,0,CW,CH); }

  // World border hint
  ctx.strokeStyle='#0f0'; ctx.lineWidth=2; ctx.globalAlpha=0.3;
  ctx.strokeRect(1,1,CW-2,CH-2);
  ctx.globalAlpha=1;
}

function drawMinimap(){
  let mc=mmCanvas, mx=mmCtx;
  mc.style.display='block';
  mx.fillStyle='#000'; mx.fillRect(0,0,120,80);
  let sx=120/WW, sy=80/WH;
  // World zones
  mx.fillStyle='#001a3a'; mx.fillRect(0,80*0.7,120,80*0.3);
  mx.fillStyle='#1a1200'; mx.fillRect(0,80*0.4,120,80*0.3);
  // Enemies
  for(let e of enemies){
    if(!e.alive) continue;
    mx.fillStyle='#0a0'; mx.fillRect(e.wx*sx-1,e.wy*sy-1,3,3);
  }
  for(let a of aliens){
    if(!a.alive) continue;
    mx.fillStyle='#80f'; mx.fillRect(a.wx*sx-1,a.wy*sy-1,3,3);
  }
  // Squad
  mx.fillStyle='#0ff';
  for(let v of squad){ mx.fillRect(v.wx*sx-2,v.wy*sy-2,4,4); }
  // Camera viewport
  mx.strokeStyle='#0f0'; mx.lineWidth=1;
  mx.strokeRect(cam.x*sx,cam.y*sy,CW*sx,CH*sy);
  mx.strokeStyle='#0a0'; mx.strokeRect(0,0,120,80);
}

function endGame(win){
  gameRunning=false; cancelAnimationFrame(animId);
  if(win){
    document.getElementById('win').style.display='block';
    document.getElementById('win').innerHTML='YOU WIN!! 🎉 SCORE: '+score+'<br><button class="btn" onclick="location.reload()">PLAY AGAIN</button>';
  } else {
    let cd=3;
    document.getElementById('gameover').style.display='block';
    document.getElementById('gameover').innerHTML='SHOT DOWN!! SCORE: '+score+'<br>Restarting in '+cd+'...';
    let t=setInterval(()=>{
      cd--;
      if(cd<=0){ clearInterval(t); document.getElementById('gameover').style.display='none'; initGame(); gameRunning=true; loop(); }
      else document.getElementById('gameover').innerHTML='SHOT DOWN!! SCORE: '+score+'<br>Restarting in '+cd+'...';
    },1000);
  }
}

// ---- DRAW FUNCTIONS ----
function drawTank(c,x,y,w,h,col,dark,flip){
  c.fillStyle=col; c.fillRect(x+4,y+h*.35,w-8,h*.55);
  c.fillStyle=dark; c.fillRect(x,y+h*.6,w,h*.4);
  c.fillStyle='#000';
  for(let i=0;i<5;i++) c.fillRect(x+i*(w/5),y+h*.62,3,h*.36);
  c.fillStyle=col; c.fillRect(x+w*.25,y,w*.45,h*.4);
  if(flip) c.fillRect(x,y+h*.1,w*.28,h*.12);
  else c.fillRect(x+w*.7,y+h*.1,w*.32,h*.12);
  c.fillStyle='#ff0';
  c.fillRect(flip?x+w*.5:x+w*.38, y+h*.08, 8, 8);
}

function drawPlane(c,x,y,w,h){
  c.fillStyle='#0f0'; c.fillRect(x+8,y+h*.3,w-8,h*.4);
  c.fillStyle='#0a0'; c.fillRect(x+w-12,y+h*.35,14,h*.3);
  c.fillStyle='#0c0'; c.fillRect(x+10,y,w*.5,h*.35); c.fillRect(x+10,y+h*.65,w*.5,h*.35);
  c.fillStyle='#080'; c.fillRect(x,y+h*.15,14,h*.7);
  c.fillStyle='#0f0'; c.fillRect(x+w*.5,y+h*.1,w*.35,4); c.fillRect(x+w*.5,y+h-4,w*.35,4);
  c.fillStyle='#aff'; c.fillRect(x+w*.55,y+h*.32,16,14);
}

function drawBoat(c,x,y,w,h){
  c.fillStyle='#0a0'; c.fillRect(x+8,y+h*.4,w-8,h*.55);
  c.fillStyle='#0f0'; c.fillRect(x+4,y+h*.25,w-4,h*.18);
  c.fillStyle='#080'; c.fillRect(x+w-10,y+h*.3,12,h*.6); c.fillRect(x,y+h*.35,10,h*.5);
  c.fillStyle='#0d0';
  for(let i=0;i<7;i++) c.fillRect(x+10+i*10,y+h*.05,6,h*.22);
  c.fillStyle='#ff0'; c.fillRect(x+w*.7,y+h*.28,3,3);
}

function drawUFO(c,x,y,w,h){
  let pulse=0.7+0.3*Math.sin(frame*.1);
  c.fillStyle=`rgba(180,0,255,${pulse})`;
  c.beginPath(); c.ellipse(x+w/2,y+h*.3,w*.28,h*.5,0,0,Math.PI*2); c.fill();
  c.fillStyle='#88f';
  c.beginPath(); c.ellipse(x+w/2,y+h*.65,w*.5,h*.3,0,0,Math.PI*2); c.fill();
  let cols=['#f00','#ff0','#0ff'];
  for(let i=0;i<3;i++){
    c.fillStyle=cols[(i+Math.floor(frame/8))%3];
    c.beginPath(); c.arc(x+w*.25+i*w*.25,y+h*.7,4,0,Math.PI*2); c.fill();
  }
  if(Math.sin(frame*.05+x)>0.5){ c.fillStyle='rgba(255,255,0,0.12)'; c.fillRect(x+w*.35,y+h*.8,w*.3,40); }
}
</script>
</body>
</html>
"""

components.html(game_html, height=760, scrolling=False)
