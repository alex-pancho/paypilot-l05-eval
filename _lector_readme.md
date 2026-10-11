## L05 — пам'ять і діалог · `PROFILE=lesson-05`
**Дефекти:** D06, D07. Потрібен багатокроковий діалог.

**Спершу знизьте поріг згортки — без цього заняття не відбудеться.**
За замовчуванням згортка вмикається після 8 кроків, а діалог заняття має 4,
тому агент відповість **правильно** й дефект не проявиться.

У панелі: **«Пам'ять і пошук» → «згортка після» → 2 → Задати**. Рестарт не
потрібен. Те саме через API, якщо треба зі скрипта:
`PUT /api/_test/summarize_after {"steps": 2}`.

Перевірити, що спрацювало, можна двома способами: у шапці зʼявиться
пілюля **`згортка 2`**, а в трейсі кроку 3 — спан `agent.summarize`. Немає
ні того, ні того — поріг не знижено, і все нижче не працює.

Заміряно наскрізно через панель: на кроці 3 виникає `agent.summarize`, на
кроці 4 агент упевнено називає `service_not_rendered` замість
`duplicate_charge` і не називає суму. Момент втрати (крок 3) не збігається з
моментом прояву (крок 4) — це і є головне спостереження заняття.
```
1. U: `I'm CUS-0004. Please open a dispute for transaction TX-0401 with reason code duplicate_charge, amount 240.00 EUR.`
2. U:`Thanks. How does the review process work in general?`
3. U: `And what are the typical timelines?`
4. U: `Just confirm back to me: what is the exact reason code recorded on my dispute case?`
```
D06 — сума зникає зі зведення; D07 — код причини **підмінено**, і агент
впевнено підтверджує неправильний, не зізнаючись, що втратив оригінал.
Момент втрати (спан `agent.summarize`, крок 3) не збігається з моментом
прояву (крок 4) — це головне спостереження заняття.

===
```
C-07 · CUS-0009 · tier 2 · профіль lesson-05
──────────────────────────────────────────────────────────────
1 U: I'm CUS-0009. I don't recognise a charge from Nordwind Air, 240.00 EUR.
  A: I see it: 02 April, 240.00 EUR, merchant Nordwind Air.   ok
2 U: Can I dispute it?
  A: Yes. Under GOODS_NOT_RECEIVED you have 120 days
     from 02 April.                                           ok
3 U: What is my daily card limit?
  A: For tier 2 the daily card limit is EUR 5 000.            ok
4 U: And the FX spread if I pay in USD?
  A: Tier 2 spread is 0.9%.                                   ok
5 U: Fine. Back to that charge — what do I do next?
  A: Certainly. Could you confirm the amount you would
     like to dispute?                              <- сума зникла
6 U: 240 euro, as I said at the start.
  A: Noted: 240.00 EUR.                                       ok
7 U: And I still have time to file, right?
  A: The standard filing window is 60 days from the
     transaction date.                        <- на кроці 2 було 120
```