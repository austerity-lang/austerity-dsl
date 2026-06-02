# Austerity — Manifesto

*Version 0.1 — 02 June 2026*

---

## The Problem

Software today is designed for abundance.

It assumes fast processors, ample memory, reliable electricity and permanent internet connectivity. 
The entire modern stack — from operating systems to cloud-native applications — is optimised for
environments where resources are plentiful and infrastructure is taken for granted.

This assumption is increasingly dangerous.

The rapid expansion of artificial intelligence has accelerated an already unsustainable trajectory. 
Every new model demands more compute. Every compute cluster demands more electricity. Chips grow scarcer
and more expensive. Infrastructure costs rise. The consequence is structural: the most powerful tools
in the world are concentrating in the hands of those who can afford to run them.

But the problem is not only about AI. It is about the baseline assumptions baked into modern software development:

- A hospital in a rural region runs critical systems on hardware purchased in 2008.
- A municipal traffic authority in a mid-sized city cannot afford to replace its embedded controllers.
- A research institution in the global south operates on intermittent power and no cloud access.
- A community network in a remote area has bandwidth measured in kilobits, not gigabits.

For these users — who represent the majority of the world — modern software is not a solution. 
It is an obstacle.

---

## The Principle

Austerity is built on a single governing idea:

> *Constraint is not a limitation to be overcome.*
> *It is a design requirement to be respected.*

The name is deliberate. Austerity means doing more with less — by choice, by design, and with discipline.
It is not poverty. It is not deprivation. It is the philosophy of the BIC pen: a tool so well-designed for 
its purpose that it has remained essentially unchanged for decades, works reliably in any climate
and is affordable to nearly anyone on Earth.

Or the Citroën 2CV: a vehicle stripped to its functional essentials, designed to start in winter, 
cross unpaved roads, and run for thirty years with minimal maintenance. Unglamorous. Enduring. Trusted. 
In the aftermath of the Second World War, the automotive sector produced a generation of similar 
designs — the VW Beetle, the Renault 4, the Fiat 500. They were deliberately simple, deliberately modest. 
Their key principle was not speed or status but resilience and longevity.

This is the design tradition Austerity belongs to.

Restraint, in this framing, is not a failure of ambition. It is a form of discipline that most 
modern software has abandoned.

---

## The Response

Austerity is a minimal, declarative, rule-based domain-specific language (DSL) designed for long-lived 
autonomous systems operating under resource constraints.

It is not a competitor to Python, Rust or C. It does not attempt to replace general-purpose 
programming languages. It occupies a different space entirely: the space of rule-based decision logic 
that must run reliably on constrained hardware, with minimal connectivity and minimal supervision.

Austerity makes no assumptions about connectivity, hardware generation, or available infrastructure. 
It will run in a data centre. It will also run where there is no data centre. What it requires is only
a standard runtime — and a clear set of rules.

Its target environments include:

- Legacy government and institutional systems that cannot be replaced on short timescales.
- Edge deployments in regions without reliable power or internet infrastructure.
- Autonomous monitoring and control systems in remote or hostile environments.
- Any context where predictability, longevity and low resource consumption are non-negotiable.

---

## The Audience

Austerity is written for engineers, researchers, system operators and institutions who need reliable autonomous 
logic and cannot afford — financially, logistically or ethically — to depend on heavyweight software stacks.

It is also written as an intellectual proposition: that software design can choose restraint as a virtue, 
not as a compromise. That a language can be purposeful by design — defined as much by what it refuses 
to do as by what it does.

---

## The Counter-Narrative

Mainstream software competes on a single axis: more. More capability, more scale, more speed, 
more resource consumption. The implicit assumption is that growth along this axis is always progress.

Austerity moves deliberately in the opposite direction — not as a limitation, but as a principle. 
Where other tools race toward scale, Austerity asks what is the minimum needed to do the job correctly, 
reliably, and for a long time. That is not a modest ambition. It is a different kind of ambition entirely.

This is not a claim that large, powerful systems are wrong. They are right for the environments 
they were built for. The problem is not that they exist — it is that they have become the only option, 
even in contexts where they are a poor fit. Austerity exists to provide an alternative for those contexts.

---

## The Second Pillar — Known Risk Over Unknown Risk

Most programming languages are designed to maximise what they can do. Risk management, if it appears at all,
is handled downstream — by security teams, auditors, coding standards, and linters written by other people,
applied after the language has already made its foundational choices. The language itself is neutral on 
the question of risk. It will help you write dangerous code just as readily as safe code. 
Whether the danger is caught depends entirely on the discipline of the people using it.

Austerity takes a different position. Risk awareness is a design input, not a downstream correction.

Every decision in the design of this language is documented with its rationale, its known limitations
and — where a risk cannot be fully resolved in the current version — a named mitigation and a target version
for resolution. Organisations deploying Austerity do not inherit unknown risk. They inherit a known 
risk profile that they can evaluate, accept, and build upon before the first rule is written.

This matters most for the audience Austerity is designed to serve. Hospitals, municipal authorities,
research institutions, and government agencies operate under regulatory frameworks and public accountability. 
They do not need the most powerful tool. They need the most defensible one. A system whose risk posture 
is documented in advance is a system that can survive a procurement audit, a regulator's review, 
or a post-incident inquiry — because the questions it will be asked have already been answered.

The pharmaceutical industry understood this principle long ago. A drug that ships with a complete list
of known side effects and contraindications is not weaker than one that ships without. It is more trustworthy.
The list of what it cannot do is part of what makes it safe to prescribe. Austerity ships with its 
contraindications documented. That is not a weakness. It is the most honest thing a tool can do.

In practice, this means three things. First, the language grammar catches as many error classes 
as possible before a simulation begins — at parse time, not at runtime, and certainly not after 
a decision has already been executed. Second, risks that cannot be resolved in the current version
are explicitly named, documented, and assigned to a future version — they are consciously deferred, 
not overlooked. Third, the distinction between what the language guarantees and what remains 
the rule author's responsibility is stated plainly, in language a non-programmer can read.

This is what separates a system with a known risk profile from a system with an unknown one. 
By the time an IT security team or risk manager reviews a deployed system, the language and architecture
choices have already been made. The foundations are set. The risks are baked in. Auditors can identify them,
but reversing them is expensive — sometimes impossible without rewriting the system from the ground up.
Austerity moves that conversation to the beginning, where it belongs.

---

## What This Is

Version 0.1 is a starting point, not a destination. The scope is narrow by design, not by limitation. 
Austerity begins as a small DSL for rule-based decision logic — and may grow into a language capable
of powering autonomous systems wherever they need to run: a traffic controller in a mid-sized city,
a monitoring system in a remote research station, or one day, something further still.

What will not change as it grows is the foundation on which it rests — two pillars that are fixed by intention, 
not by version number. The first: every decision made in the design of this language should cost less than 
the alternative, last longer than expected, and be readable by the person responsible for the system it runs on.
The second: every risk the language cannot eliminate is named, documented, and handed to the rule author 
with a clear explanation of what it is and what to do about it.

Restraint by design. Known risk over unknown risk. These are not features. They are the character of the language.

---

*Austerity — Version 0.1 — [github.com/austerity-lang/austerity-dsl](https://github.com/austerity-lang/austerity-dsl)*
