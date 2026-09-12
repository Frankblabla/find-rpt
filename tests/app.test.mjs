import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { groupEstimates, revisionDisplay } from '../static/estimates.mjs';

const source = fs.readFileSync(new URL('../static/app.js', import.meta.url), 'utf8').replace(/^import .*\n/, '');
const tick = () => new Promise(resolve => setImmediate(resolve));
function ui() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '', checked: false, disabled: false, html: '', buttons: [],
      get innerHTML() { return this.html; },
      set innerHTML(value) {
        this.html = value;
        this.buttons = [...value.matchAll(/<button data-report="([^"]+)"([^>]*)>/g)].map(m => ({
          dataset: { report: m[1] }, disabled: m[2].includes('disabled'),
          hasAttribute: name => name === 'data-manual' && m[2].includes('data-manual'),
        }));
      },
      querySelectorAll(selector) {
        if (selector === '[data-report]') return this.buttons;
        if (selector === '[id^="confirm-"]') return [...this.html.matchAll(/id="(confirm-[^"]+)"/g)].map(m => Object.assign(element(m[1]), {id:m[1]}));
        return [];
      },
      querySelector(selector) { return this.buttons.find(b => selector.includes(b.dataset.report)); },
    });
    return elements.get(id);
  }
  let fetcher = async path => path === '/api/catalog' ? {
    models:['opus'], efforts:['high'], default_model:'opus', default_effort:'high', brokers:['Test'], total:101, development:88, acceptance:13,
  } : [];
  const context = vm.createContext({
    document: { getElementById:element, addEventListener(){}, querySelectorAll(){return [];} },
    groupEstimates, revisionDisplay, console, setTimeout: fn => { fn(); },
    fetch: async (path, options) => ({ok:true, json:async () => fetcher(path, options)}),
  });
  vm.runInContext(source, context);
  return {element, context, setFetch: fn => {fetcher = fn;}, search: () => element('search').onsubmit({preventDefault(){}})};
}
const candidate = (ticker, id='a') => ({status:'no_match', candidates:[], review_candidates:[{id, ticker, file:'Example.pdf', split:'acceptance'}]});

test('lookup clears old confirmations and discards stale lookup responses', async () => {
  const u=ui(); await tick();
  const pending=[];
  u.setFetch((path, options) => new Promise(resolve => pending.push({resolve, body:JSON.parse(options.body)})));
  u.element('matches').innerHTML='Old confirmed file';
  u.element('ticker').value='ABC LN'; const first=u.search(); await tick();
  assert.equal(u.element('matches').innerHTML,'');
  u.element('ticker').value='XYZ LN'; const second=u.search(); await tick();
  pending[1].resolve(candidate('XYZ LN','new')); await second;
  pending[0].resolve(candidate('ABC LN','old')); await first;
  assert.match(u.element('matches').innerHTML,/XYZ LN/);
  assert.doesNotMatch(u.element('matches').innerHTML,/ABC LN|data-report="old"/);
});

test('manual card submits its captured lookup ticker even when the input changes', async () => {
  const u=ui(); await tick();
  const posted=[];
  u.setFetch(async (path, options) => {
    if(path==='/api/lookup') return candidate('ABC LN');
    if(path==='/api/runs' && options?.body) {posted.push(JSON.parse(options.body)); return {id:'synthetic'};}
    if(path==='/api/runs/synthetic') return {status:'failed', error:'Synthetic stop'};
    return [];
  });
  u.element('ticker').value='ABC LN'; await u.search();
  const button=u.element('matches').buttons[0];
  assert.equal(button.disabled,true);
  u.element('confirm-a').checked=true; u.element('confirm-a').onchange();
  assert.equal(button.disabled,false);
  u.element('ticker').value='XYZ LN'; button.onclick(); await tick();
  assert.equal(posted.length,1);
  assert.equal(posted[0].ticker,'ABC LN'); assert.equal(posted[0].confirm_selection,true);
});

test('manual notice survives source confirmation and mismatch hides all brief and draft content', async () => {
  const u=ui(); await tick();
  const fact={text:'Synthetic brief content',sources:['p1l1'],kind:'broker'};
  const result={report:{id:'a',broker:'Test'},request:{ticker:'ABC LN',lookup_date:'20260511',selection:{method:'user_confirmed'}},brief:{
    title:'Example',report_date:'2026-05-11',subject_match:'confirmed',identity:fact,takeaway:fact,
    changes:[],estimates:[],drivers:[],context:fact,estimate_picture:fact,material:[],answer:[],limitations:[],
    email_draft:{analyst:'Analyst',to:'a@example.test',subject:'Question',body:'Synthetic draft content',sources:['p1l1']},
  },comparisons:[]};
  u.context.fixture=result;
  for(const assessment of ['confirmed','ambiguous']) {
    result.brief.subject_match=assessment; vm.runInContext('render(fixture)',u.context);
    assert.match(u.element('result').innerHTML,/User-confirmed file selection; cover ticker unverified/);
    assert.match(u.element('result').innerHTML,/Synthetic draft content/);
    assert.doesNotMatch(u.element('result').innerHTML,/No email drafted|Email draft unavailable/);
  }
  result.brief.subject_match='mismatch'; result.brief.identity={...fact,text:'Wrong subject'};
  vm.runInContext('render(fixture)',u.context);
  assert.match(u.element('result').innerHTML,/Wrong subject/);
  assert.doesNotMatch(u.element('result').innerHTML,/Synthetic brief content|Synthetic draft content|What changed|Ask a follow-up/);
});

test('email status explains no revisions, a stated cause, or a missing required draft', async () => {
  const u=ui(); await tick();
  const fact={text:'Synthetic statement',sources:['p1l1'],kind:'broker'};
  const fixture={report:{id:'a',broker:'Test'},request:{ticker:'ABC LN',lookup_date:'20260511'},brief:{
    title:'Example',report_date:'2026-05-11',subject_match:'confirmed',identity:fact,takeaway:fact,
    changes:[],estimates:[],drivers:[],context:fact,estimate_picture:fact,material:[],answer:[],limitations:[],
    email_draft:null,
  },comparisons:[]};
  for (const [revisions,rationale,message] of [
    [false,'not_applicable','no estimate revisions were identified'],
    [true,'clear','the report explains the identified estimate revisions'],
    [true,'unclear','Email draft unavailable'],
  ]) {
    Object.assign(fixture.brief,{revisions_present:revisions,rationale});
    u.context.fixture=fixture; vm.runInContext('render(fixture)',u.context);
    assert.ok(u.element('result').innerHTML.includes(message));
    assert.equal(u.element('result').innerHTML.includes('No email drafted:'), !revisions || rationale==='clear');
  }
});
