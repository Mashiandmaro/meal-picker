import {RECIPES, TYPES, MEALS, SCENES, EXCLUSIONS, ROLES} from './data.js';
export const STORAGE_KEY='good-meal:v1';
export function defaults(){return {version:1,meal:new Date().getHours()<10?'breakfast':new Date().getHours()<15?'lunch':'dinner',type:'lean',scene:'all',favorites:[],custom:[],history:[],excluded:[],recent:[],current:null};}
export function allRecipes(state){return [...state.custom,...RECIPES];}
export function allowed(recipe,excluded){return !recipe.parts.some(p=>p.tags.some(t=>excluded.includes(t)));}
export function candidates(state,{query='',favoritesOnly=false,allMeals=false}={}){
 const q=query.trim().toLocaleLowerCase();
 return allRecipes(state).filter(r=>(allMeals||r.meals.includes(state.meal))&&(state.type==='all'||r.type===state.type)&&(state.scene==='all'||r.scenes.includes(state.scene))&&allowed(r,state.excluded)&&(!favoritesOnly||state.favorites.includes(r.id))&&(!q||[r.title,...r.parts.map(p=>p.name)].join(' ').toLocaleLowerCase().includes(q)));
}
export function pick(state,options={}){const list=candidates(state,options);if(!list.length)return null;let pool=list.filter(r=>r.id!==state.current?.id&&!state.recent.includes(r.id));if(!pool.length)pool=list.filter(r=>r.id!==state.current?.id);if(!pool.length)pool=list;return structuredClone(pool[Math.floor(Math.random()*pool.length)]);}
const bounded=(v,n)=>typeof v==='string'&&v.trim().length>0&&v.length<=n;
export function validateRecipe(r){
 return r&&bounded(r.id,100)&&bounded(r.title,60)&&Object.hasOwn(TYPES,r.type)&&Array.isArray(r.meals)&&r.meals.length>0&&r.meals.length<=3&&r.meals.every(m=>Object.hasOwn(MEALS,m))&&Array.isArray(r.scenes)&&r.scenes.length>0&&r.scenes.length<=3&&r.scenes.every(s=>s!=='all'&&Object.hasOwn(SCENES,s))&&Array.isArray(r.parts)&&r.parts.length===3&&new Set(r.parts.map(p=>p?.role)).size===3&&r.parts.every(p=>p&&bounded(p.id,100)&&bounded(p.name,80)&&Object.hasOwn(ROLES,p.role)&&Array.isArray(p.tags)&&p.tags.length<=20&&p.tags.every(t=>EXCLUSIONS.includes(t))&&Array.isArray(p.scenes)&&p.scenes.every(s=>Object.hasOwn(SCENES,s)))&&typeof r.tip==='string'&&r.tip.length<=500&&['custom','curated','adapted'].includes(r.source)&&Number.isInteger(r.art)&&r.art>=0&&r.art<=3;
}
export function validateState(raw){
 if(!raw||raw.version!==1||!Object.hasOwn(MEALS,raw.meal)||!(raw.type==='all'||Object.hasOwn(TYPES,raw.type))||!Object.hasOwn(SCENES,raw.scene))throw Error('备份格式不正确或版本不支持');
 for(const key of ['favorites','custom','history','excluded','recent'])if(!Array.isArray(raw[key]))throw Error('备份缺少必要内容');
 if(raw.custom.length>500||raw.favorites.length>600||raw.history.length>200||raw.recent.length>50||raw.excluded.length>EXCLUSIONS.length)throw Error('备份内容超过支持的数量');
 if(!raw.custom.every(r=>validateRecipe(r)&&r.id.startsWith('custom-'))||new Set(raw.custom.map(r=>r.id)).size!==raw.custom.length)throw Error('自定义搭配数据不完整');
 const ids=new Set([...RECIPES,...raw.custom].map(r=>r.id));
 if(!raw.favorites.every(id=>ids.has(id))||!raw.excluded.every(t=>EXCLUSIONS.includes(t))||!raw.recent.every(id=>bounded(id,100)))throw Error('备份包含无效的收藏或偏好');
 if(!raw.history.every(h=>h&&validateRecipe(h.recipe)&&bounded(h.date,40)&&!Number.isNaN(Date.parse(h.date))&&Object.hasOwn(MEALS,h.meal)))throw Error('饮食选择记录不完整');
 if(raw.current!==null&&!validateRecipe(raw.current))throw Error('当前搭配数据不完整');
 const clean=defaults();for(const key of Object.keys(clean))clean[key]=structuredClone(raw[key]);return clean;
}
