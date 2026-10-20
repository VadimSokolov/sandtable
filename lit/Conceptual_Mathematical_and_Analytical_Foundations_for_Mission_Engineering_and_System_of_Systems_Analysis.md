

# Conceptual, Mathematical, and Analytical Foundations for Mission Engineering and System of Systems Analysis

Ali K. Raz ![](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/666e09182d4cd268646ea700ea60dcdf_img.jpg), *Senior Member, IEEE*, Mohammed Bhuyian, Jose L. Bricio-Neto, Christopher Santos ![](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/1ef1ef0bf9af6c6996401964cf280f2d_img.jpg), and Daniel Maxwell

**Abstract**—Mission engineering (ME) is an emerging approach to designing and analyzing configurations of system-of-systems (SoS) for accomplishing one or more missions. ME seeks to flexibly leverage SoS capabilities and dynamically adapt their configuration to meet evolving mission needs. SoS configurations today, however, remain static and are carefully designed to accomplish a mission. The problem we address in this article is developing modeling and analysis techniques for flexible integration and adaptive selection of potential SoS configurations to achieve multiple missions with an overarching agility in the execution space. We propose a foundational framework for ME, complete with semantics and grammar to represent the ME design space (MEDS), along with a set of logical and mathematical modeling approaches that lends the MEDS to robust SoS analytical methods. Specifically, the framework proposes development of a mission-focused ontology and domain-specific language to enable consistent semantic representation of MEDS, which is then logically evaluated for spatial and temporal consistency in forming SoS configurations using set-based design principles and Allen’s interval algebra. The resulting feasible SoS configurations are then evaluated for mission success using graph theory and multiattribute utility theory. The application of the framework is demonstrated on a simplified and notional sense-decide-effect problem for flexibly accomplishing multiple missions with SoS.

**Index Terms**—Allen’s interval algebra (AIA), complex systems analysis, mission engineering (ME), set-based design (SBD), system of systems (SoS).

## I. INTRODUCTION

**E**NGINEERING to achieve novel capabilities and accomplish challenging tasks in modern society involves integrating multiple complex systems [1]. In systems engineering (SE), these challenges fall under the purview of system-of-systems engineering (SoSE), where multiple operationally and

managerially independent systems are integrated into an overarching solution [2]. Consider, for example, network-centric military command and control (C2) scenarios integrating systems from multiple operating domains [3], [4], disaster relief scenarios for integrating capabilities of multiple multinational organizations [5], [6], or intelligent transportation networks of autonomous vehicles with vehicle-to-vehicle and vehicle-to-infrastructure communication for rapid planning and decision-making.

SoSE architecting, design, and evaluation has a well-established and evolving body of knowledge, which over the past few decades has examined different aspects of SoSE [7]. However, a major limitation of SoSE techniques is that they can be brittle and SoS architectures once implemented are difficult to change because the role, capabilities, and integration of constituent systems are rigidly defined and engineered [2], [8]. Given today’s evolving mission needs, and advanced (especially autonomous) systems, there is a critical need to explore and exploit capabilities of the same set of constituent systems toward achieving more than one mission. This demands an evolution of current SE and SoSE development paradigms to be flexible and agile in response to changing mission needs [9], but as noted in [10], there is very limited work done in dynamic evolution and evolving architectures for SoS.

Analysis techniques that provide the ability to integrate multiple systems that are designed and acquired independently to satisfy demands of one or more missions is termed as “mission engineering (ME)” [11]. From the ME perspective, a suite of high valued SoS configurations that balance different objectives, such as timeliness, interoperability, risk, and performance may be more desirable than a single optimal solution. Point solutions that are “optimal” for a single situation lack the agility to adjust to unanticipated changes in the SoS, often necessitated by changes in the environment that are beyond the control of individual system owners.

The purpose of this article is to advance the ME for SoS by establishing a conceptual and mathematical formulation that lends itself for employing a set of analytical methods that help comprehend and analyze a combinatorically explosive mission engineering design space (MEDS). The conceptual, mathematical, and analytical methods then help identify flexible, adaptive, and feasible SoS configurations that are reconfigurable for achieving multiple missions.

Manuscript received 5 February 2024; revised 23 April 2024; accepted 31 May 2024. Date of publication 25 July 2024; date of current version 20 September 2024. This work was supported by the Defense Advanced Research Projects Agency (DARPA) under Contract 47QFLA19D0003 and Contract HR0011-21-C-0037. (*Corresponding author: Ali K. Raz.*)

Ali K. Raz and Mohammed Bhuyian are with the Systems Engineering and Operations Research Department, George Mason University, Fairfax, VA 22030 USA (e-mail: [araz@gmu.edu](mailto:araz@gmu.edu)).

Jose L. Bricio-Neto is with the Rapid Prototyping Research Center, George Mason University, Springfield, VA 22150 USA.

Christopher Santos is with the LinQuest Corporation, Reston, VA 20171 USA.

Daniel Maxwell is with the KadSci LLC, Fairfax, VA 22030 USA.

Digital Object Identifier 10.1109/JSYST.2024.3409231

The major contributions of this article are a unifying framework for representing MEDS, identifying feasible SoS configurations, and conducting preliminary architectural evaluations to establish performance expectations. This framework is built on three interdependent steps that facilitate machine interpretation and reasoning of the MEDS via:

- 1) an ontological foundation for logical and semantic analysis;
- 2) a mathematical formulation for logical reasoning to identify feasible architectures;
- 3) pairing 1 and 2 with formal analytical methods for evaluation of potential SoS configurations.

We introduce a domain-specific language (DSL), which provides a graph-based semantics to describe and distill the MEDS. The DSL is then paired with a set-based mathematical notation and Allen's interval algebra (AIA) [12] to provide a mathematical and logical constructs to represent the key elements of the MEDS. This notation includes explicit representation of spatial hierarchy and temporal dependencies between systems that execute SoS tasks. Finally, we introduce an integrated analytical process to evaluate SoS configurations using graph theory [13] and multiutility attribute theory [14], [15]. The application of this framework is demonstrated on a notional sense-decide-effect C2 problem with a need to perform multiple missions with a set of integrated systems. While the application example is developed for C2 missions, it is emphasized throughout the development that the technical constructs of the framework are applicable across wider SoS domains (e.g., air transportation systems, smart cities, supply chains logistics, Internet of Things, etc.) [16].

The rest of this article is organized as follows. Section II introduces ME along with a comprehensive literature review and gap analysis for research needs. Section III provides the ME formulation in the SoS context while the technical details of our framework for ME-based flexible configurations of SoS are described in Section IV. Section V provides a conceptual example of the proposed methodology applied to a notional sense-decide-effect problem. Finally, Section VI concludes this article.

## II. INTRODUCTION TO ME AND RESEARCH NEEDS

### A. What is ME?

ME is an emerging term with an evolving body of the literature in SE, SoSE, and complex systems analysis that takes a top-down mission focused approach to bring together SoS capabilities to accomplish one or more objectives. The United States Department of Defense (DoD) defines ME as a deliberate planning, organization, and analysis of technological capabilities, enabled by complex systems, to achieve a desired outcome [11]. The primary idea of ME is to utilize multiple systems in operational context to perform one or more missions and identify any technical gaps in both current and future capabilities [11]. A recent SE body of knowledge article puts it succinctly by specifying ME is where mission is the “system of interest” and consequently the SoS that enable the mission, become the constituent elements of this “system of interest” [17]. ME requires extension of SE approaches to the design, architecture, analysis, and evaluation

of solutions that meet the mission needs across a wide spectrum of operational outcomes and environmental uncertainties [18], [19].

Successfully executed ME provides for the flexible integration and interoperability of multiple technologically complex systems, as most missions—ranging from military and humanitarian missions to space exploration operations and supply chains—require coordination and capability exchange between systems [17]. Although the recent emphasis on ME is mostly in a military context, one of the first uses of the term “ME” appears in space mission literature from NASA's Goddard Space Flight Center, where ME is defined as an end-to-end a multi-dimensional approach for creating a developmental process to integrate space and ground assets with science instruments and spacecraft operations toward desired mission [20]. Since ME seeks to enable consistency and coherence between SE, operations, and missions [21], it is expected that any complex situation that requires integration of technological systems—hardware or software—and SoS will benefit from ME practice.

### B. Recent ME Literature

ME is a comparatively nascent engineering field with an evolving body of literature emerging only within the last decade or so [22]. One of most recent and authoritative guidance documents on ME comes from the U.S. DoD “Mission Engineering Guide,” which lays down the required foundations of ME, while emphasizing the complexity emerging from flexible integration of already challenging SoS and the need for developing rigorous analytical methods to support ME analysis [11]. Specifically, ME needs include the following:

- 1) ability to analytically address combinatoric explosion of possibilities and ambiguity in SoS definitions;
- 2) ability to adaptively allocate tasks and reconfigure the SoS;
- 3) ability to identify a set of “good enough” SoS configurations to accomplish the mission.

The literature on ME can be divided into two major categories: one focuses on showcasing the applicability of model-based systems engineering (MBSE) practices and languages [e.g., systems modeling language (SysML)] to ME needs while the other category proposes the development/application of SoSE methods to ME problems.

Beery and Paulo advocate for the use of MBSE and demonstrate how MBSE concepts applied using SysML in early life cycle stages can enable support of ME objectives [23]. They propose to develop a flexible architecture of systems that supports ME-based evaluations where such capabilities are methodically examined during the conceptual design stages with trade space visualization. Kaslow et al. [24] proposed building a reference architecture for a given domain that can enable ME to comprehensively model mission [25]. Kaslow et al., as part of International Council of Systems Engineering Space Systems Working Group, have developed a reference architecture for CubeSat and propose capturing multiple missions as a model with SysML to perform ME. Giles and Giammarco [26] proposed a mission-based architecture for swarm composability (MASC), which allows an unmanned swarm reconfiguration for

multiple missions. MASC provides hierarchical and systematic decomposition of a mission space and phases that are then related to tactics and plays a swarm can apply to accomplish a range of missions within an MBSE framework. On the application side of SE, Lee et al. [27] have developed an MBSE digital twin of an unmanned aerial system for dynamic route planning with an ME focus, while Ziacomo et al. [28] utilized scenario-based tradeoff analysis for reuseable design of the SpaceX Falcon 9 booster for multiple missions.

In the SoSE literature, Hernandez and Pollman [29] identified integration of new systems and capabilities into an existing organization and SoSE as a key-enabler of ME practice. They posit that ME is a combination of SE paired with tactical insights to deliver SoS capabilities and propose a three phased integration approach of transition, adoption, and diffusion of capabilities for ME. Brown and Olinick [30] on the other hand, take an analytical approach to ME, formulating system-selection as a set covering problem. Their approach focuses on introducing reliability in addition to cost as a metric for system-selection to minimize life-cycle cost of systems in SoSE for ME while ensuring the system will continue to deliver mission capabilities under specified reliability requirements. Furthermore, Brown and Olicik provided a comprehensive overview of SoS analytical methods that are readily applicable for optimizing system-selection for ME. In addition to system-selection, exploiting environmental considerations to gain a tactical advantage also remains within the ME purview. Dachowicz et al. [31] have proposed a novel approach to probe mission design using large scale simulation of real-time strategy games, which is reflective of a complex battlefield operational environment and utilize explainable AI techniques to increase the likelihood of achieving desired mission outcomes.

### C. Gaps Analysis and Research Needs

It is evident from the abovementioned discussion that ME is rapidly emerging and is expected to be widely adopted across many domains. However, a pertinent challenge for ME is that there are no conceptual and mathematical frameworks available that can represent the MEDS complexity and the spectrum of possible outcomes. The ME literature review from above clearly showcases how different researchers are attempting to meet the flexible integration and system-selection challenge either at a conceptual level with MBSE or with analytical methods. Nevertheless, it is important to note that most analytical methods have specific mathematical and theoretical foundations and MBSE methods have their own conceptual representation. Many analytical methods that are used for analysis and evaluation of SoS take a static snapshot of a system, which simplifies the problem but at the same time overshadows evolution of interactions that are the source of emergent behavior and, hence, complex system behavior. A major gap here is to represent an MEDS, conceptually, mathematically, and analytically, to which results of MBSE and SoSE methods can map to. In order to advance ME and its adoption across different domains, it is imperative to first mathematically formulate the MEDS and then develop:

![Network diagram: Mission web and multiple paths for mission tasks across a network of systems.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/2df09d249c38abee55dbf0526dd6da0a_img.jpg)

Mission Web  
 $\mathcal{M}_1 = \{MT_1, MT_2, MT_3\}$   
 $\mathcal{M}_2 = \{MT_2, MT_3\}$   
 $\mathcal{M}_3 = \{MT_2, MT_1\}$   
Different missions require different task from a similar set of system  
 $t = 1, \dots, t$   
Network of systems to perform multiple mission  
 $MT_1$   
 $MT_2$   
 $MT_3$   
 $S_1$   
 $S_2 \leftarrow MT_1, S_1 \leftarrow MT_2, S_3 \leftarrow MT_3$   
Multiple paths from a set of systems to perform the mission tasks  
 $S_2$   
 $S_3 \leftarrow MT_1, S_2 \leftarrow MT_2, S_1 \leftarrow MT_3$   
 $S_3$   
 $S_1 \leftarrow MT_1, S_2 \leftarrow MT_2, S_3 \leftarrow MT_3$   
Paths to complete mission tasks  
Set of mission tasks for given mission  
 $MT_1$   
 $MT_2$   
 $MT_3$

A diagram illustrating a mission web with three systems (S1, S2, S3) and three mission tasks (MT1, MT2, MT3). Below, multiple paths through the systems are shown to complete the tasks, with a linear sequence of MT1, MT2, and MT3 at the bottom.

Network diagram: Mission web and multiple paths for mission tasks across a network of systems.

Fig. 1. ME problem formulation (as an OV-1 diagram).

- 1) consistent semantics that distill the conceptual formulation of MEDS for analytical analysis;
- 2) mathematical formulation(s), which builds on the consistent semantics, and conceptually represents the solutions space of multiple missions;
- 3) analytical methods that can prescreen feasibility and efficacy of solutions to reduce the MEDS prior to the application of modeling and simulation and SoS engineering analytical methods.

The rest of this article is focused on developing a mathematical formulation of MEDS and addressing the abovementioned three items.

## III. ME PROBLEM FORMULATION

The problem we address in this article is developing consistent modeling and analysis techniques for flexible integration and adaptive selection of potential SoS architecture(s) to achieve multiple missions with an overarching agility in the execution space. The motivation for such flexible integration and adaptability is evident from the ME literature emerging across multiple domains, e.g., in defense sector [11], [22], disaster response [5], and the Industry 4.0 initiatives in commercial and industrial sectors [32]. A common SoS challenge across these domains is that there are multiple missions that need to be accomplished, each mission requires a set of mission tasks (MTs) to be completed by a set of distributed systems that can perform one or more of these MTs. This concept is illustrated in Fig. 1 as an Operational view (OV-1) diagram [33].

Mathematically, we can use set-based notation to describe the MEDS. Let  $\Omega_{\text{MEDS}} = \{\mathcal{M}_1, \mathcal{M}_2, \dots, \mathcal{M}_m\}$  be the MEDS defined by a set of  $m$  missions. Here, each mission requires one or more (say  $n$ ) MT to be completed in a predefined partially ordered manner, i.e.,  $\{\text{MT}_1 \text{ precedes } \text{MT}_2 \text{ followed by } \text{MT}_n\}$ . These tasks can be accomplished by a set of systems, i.e.,  $S = \{S_1, S_2, \dots, S_s\}$ , where one system may perform more than one task at a given time. We define the following terms to describe the MEDS, adapted from [34], and their corresponding mathematical notation is developed in Section IV-B:

![Flowchart: Framework for mission engineering design space and system of systems configurations.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/9e6062272bbe3ddbb7c0606721d64cf0_img.jpg)

Mission Engineering Design Space: Concept of operations requiring distributed complex adaptive systems and system of systems  
Ontological Foundations  
Provide a lexicon, taxonomy, and grammar for MMO  
Formal Semantic Representation via Domain Specific Language  
Common representation across a multidisciplinary ecosystem  
Mathematical Formulation  
Develop logically consistent, scalable, and mathematical representation  
 $MW : \mathcal{MN} \rightarrow \Omega_{MEDS}$   
 $\mathcal{MN}_{\mathcal{M}_i} = \{MP_{1\mathcal{M}_i}, MP_{2\mathcal{M}_i}, ..., MP_{L\mathcal{M}_i}\}$   
 $\forall \mathcal{M}_i \in \Omega_{MEDS} \exists \mathcal{MN}_i \in \mathcal{MN} | \mathcal{M}_i = MW$   
Set-based Design + Allen's Interval Algebra  
Machine interpretability of MEDS  
Analytical Formalism  
Provide an analytical reasoning and analysis engine for capability engineering  
Graph Theory  
Multi-Attribute Utility Theory  
Metrics and methods for large interdependent design spaces  
Flexible, dynamic, and feasible System of Systems configurations for meeting mission objectives

```
graph TD
    A["Mission Engineering Design Space: Concept of operations requiring distributed complex adaptive systems and system of systems"] --> B["Ontological Foundations<br>Provide a lexicon, taxonomy, and grammar for MMO<br>Formal Semantic Representation via Domain Specific Language<br>Common representation across a multidisciplinary ecosystem"]
    A --> C["Mathematical Formulation<br>Develop logically consistent, scalable, and mathematical representation<br>MW : MN -> Omega_MEDS<br>MN_Mi = {MP1_Mi, MP2_Mi, ..., MPL_Mi}<br>forall Mi in Omega_MEDS exists MNi in MN | Mi = MW<br>Set-based Design + Allen's Interval Algebra<br>Machine interpretability of MEDS"]
    A --> D["Analytical Formalism<br>Provide an analytical reasoning and analysis engine for capability engineering<br>Graph Theory<br>Multi-Attribute Utility Theory<br>Metrics and methods for large interdependent design spaces"]
    B --> C
    C --> D
    B --> E["Flexible, dynamic, and feasible<br>System of Systems configurations for meeting mission objectives"]
    C --> E
    D --> E
```

A block diagram showing a framework connecting Mission Engineering Design Space to Ontological Foundations, Mathematical Formulation, and Analytical Formalism, which all lead to flexible, dynamic, and feasible System of Systems configurations.

Flowchart: Framework for mission engineering design space and system of systems configurations.

Fig. 2. ME ontological, mathematical, and analytical framework.

**Definition 1 (Mission Chain (MC)):** An MC is defined as a set and sequence of MT required to achieve a mission objective.

**Definition 2 (Mission Path (MP)):** An MP is defined as a set of all feasible allocations of  $S \leftarrow \text{MT}$  to complete the required sequence of MTs indicated in an MC by available systems in the SoS.

**Definition 3 (Mission Net (MN)):** An MN is defined as a set of all feasible MP available to perform a given mission, say  $\mathcal{M}_n \in \Omega_{\text{MEDS}}$ .

**Definition 4 (Mission Web (MW)):** An MW is defined as a set of MN for all missions in the MEDS, where MW provides a one-to-one and onto mapping of MN to  $\Omega_{\text{MEDS}}$ .

With the abovementioned problem formulation, there are two major research questions that we seek to address in this article: first is how to identify the feasible set of MP for different objectives and form an MN given that systems are shared across the MW, and, second, is how to establish a performance evaluation scheme to distinguish between multiple feasible MP in the MW.

## IV. UNIFYING FRAMEWORK FOR ME AND SYSTEM OF SYSTEMS ANALYSIS

In this section, we propose a framework to distill the MEDS for machine interpret-ability and reasoning for application of computational methods for an SoS. SoSE, as initially introduced by Meir [2], contained three types of SoS: Directed, collaborative, and virtual, whereas a fourth type of acknowledged SoS was subsequently introduced by Dahmann and Baldwin [35]. In this sample case, we are using MEDS to represent, identify, and evaluate potential MWs, -nets, and -paths. The tools and techniques discussed herein are deemed most effective for directed

and acknowledged SoS and useful for pruning the search space to eliminate infeasible system configurations in an SoS.

This framework (illustrated in Fig. 2) begins with a specification of MEDS that begins with the concept of operations (such as DoD architecture framework [33] OV-1 diagrams commonly found in the SE literature, e.g., Fig. 1) and details the SoS mission objectives and available resources [36]. Building on the SoS problem description and MEDS, this framework then develops an ontological foundation, mathematical formulation, and an analytical formalism for the creation of flexible, dynamic, and feasible SoS configuration that encompass the MW for meeting the mission objectives. This section provides the conceptual and theoretical details for building the three steps of this framework, while Section V provides an application example to a notional ME problem.

### A. Ontological Foundations

The use of an ontology is a mechanism for significantly reducing uncertainty caused by ambiguity in terms, especially when multiple technical and operational disciplines are involved in problem formulation and execution. This is particularly important for ME and SoS problems where the mission design space, objectives, metrics, and capabilities of technical systems require esoteric subject matter expertise from strategic operations, engineering and science, tactical operations, and logistics.

The approach we adopted for ME is to develop a DSL that provides a *semantically consistent* representation of the MEDS across various disciplines. The DSL provides a foundation for executing the later stages of the ME framework. A DSL is an applied ontology that is tailored to the SoS and operating

TABLE I  
DSL EXAMPLE

|                   | Ontological constructs | Military SoS DSL                       | Air transportation SoS DSL             |
|-------------------|------------------------|----------------------------------------|----------------------------------------|
| <b>Actors</b>     | <b>Entity</b>          | Sensors, deciders, effectors, etc.     | Aircraft, airport, control tower etc.  |
|                   | <b>Properties</b>      | Range, location, speed, capacity, etc. | Throughput, range, speed, etc.         |
| <b>Objectives</b> | <b>Entity</b>          | Objects                                | Deliver cargo, execs, passengers, etc. |
|                   | <b>Properties</b>      | Location, priority, lethality, etc.    | Priority, cost, etc.                   |
| <b>MTs</b>        | <b>Entity</b>          | Find, fix, track, engage, etc.         | Load, unload, depart, Land, etc.       |
|                   | <b>Properties</b>      | Time, pre-reqs, uncertainty, etc.      | Time, sequence, Cost, etc.             |
|                   | <b>Dependence</b>      | Only sensor can perform find and fix   | Cargo planes cannot carry passengers   |

![UML diagram: UML class diagram of an ontology with owl:Thing at the center.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/53f1f7d17b3e7aae62169c41d2a88a77_img.jpg)

Effectors  
Location  
Lethality  
Deciders  
Sensors  
Objectives\_Prop  
erties  
Priority  
Range  
Actors\_Entity  
Actors  
Objectives  
Objectives\_Enti  
ty  
Objects  
Speed  
Actors\_Properti  
es  
owl:Thing  
Capacity  
Position\_Locall  
on  
Time  
Mission\_Tasks  
MT\_Entity  
Fix  
Engage  
MT\_Properties  
Track  
Find  
Uncertainty  
Pre-reqs

```
classDiagram
    owl:Thing <|-- Actors
    owl:Thing <|-- Mission_Tasks
    owl:Thing <|-- MT_Properties
    Actors <|-- Actors_Entity
    Actors <|-- Actors_Properti
es
    Actors_Entity <|-- Deciders
    Actors_Entity <|-- Effectors
    Actors_Entity <|-- Sensors
    Actors_Properti
es <|-- Range
    Actors_Properti
es <|-- Speed
    Actors_Properti
es <|-- Capacity
    Actors_Properti
es <|-- Position_Locall
on
    Mission_Tasks <|-- Time
    Mission_Tasks <|-- MT_Entity
    MT_Properties <|-- Uncertainty
    MT_Properties <|-- Pre-reqs
    MT_Entity <|-- Track
    MT_Entity <|-- Find
    MT_Entity <|-- Engage
    MT_Entity <|-- Fix
    Objectives <|-- Objectives
    Objectives <|-- Objectives_Prop
erties
    Objectives <|-- Objectives_Enti
ty
    Objectives_Prop
erties <|-- Location
    Objectives_Prop
erties <|-- Lethality
    Objectives_Prop
erties <|-- Priority
    Objectives_Enti
ty <|-- Objects
```

A UML class diagram showing a hierarchy of classes inheriting from owl:Thing, which is highlighted in a green box. Classes include Actors, Mission\_Tasks, MT\_Properties, and Objectives, along with their respective sub-classes and properties.

UML diagram: UML class diagram of an ontology with owl:Thing at the center.

Fig. 3. Partial DSL and ontology for simplified C2 SoS—Output from Protégé (which is RDF compliant open source ontology software).

environment of interest and emphasizes the development of clearly defined, machine readable representations of SoS components, component behaviors, and relevant elements of the environment [37]. A DSL along with the corresponding ontology specifies all the entities, entity properties, entity relationship, and entity dependence that are present within the MEDS. Three major top-level constructs in the proposed ontology are actors, objectives, and MTs. Actors contain the set of systems and their properties; MTs are the all-inclusive set of tasks along with their properties and dependence on actors and other tasks, and objectives are multiple missions included in the MEDS. Building on these three ontological constructs, a DSL, as the name implies, provides a domain-specific stipulation of the mission space that should remain consistent across mission formulation and execution. Table I provides an example of a partial DSL for two different operational domains, a military C2 DSL derived from the find, fix, track, target, engage, and assess tasks [38] and the other from the air transportation domain [39].

An important aspect to note here is that while the DSL definitions remain different across domains, the overarching ontological constructs and structure are consistent. Both the ontological constructs along with the DSL play significant roles in the follow on steps of the proposed ME framework. It is suggested that the DSL for MEDS be developed in graphical relational databases (e.g., resource description framework (RDF) [40]). An example RDF compliant output of DSL and ontology presented in Table I is illustrated in Fig. 3, which graphically depicts the relationships and constraints for actors, objects, and tasks dependencies. This

enables automated mathematical and analytical reasoning for constructing missions chains, paths, nets, and webs as defined earlier in Section III.

The above highly focused approach leverages the underlying information and computer science benefits that an ontology provides when analyzing complex systems without becoming bogged down in more philosophical ontological standards debates (e.g., basic formal ontology versus dublin core versus unified formal ontology, etc.) [41]. Moreover, this approach recognizes the limits of semantic reasoning and provides for the injection of different analytic techniques that leverage the logically and semantically consistent foundation an ontology provides.

### B. Mathematical Formulation

The MW sits at the top level of the hierarchy in an MEDS while the MT and MC are at the atomic level. A fundamental requirement for ME is to maintain consistent linkage throughout this hierarchical decomposition, which must be explored and exploited for achieving multiple missions. In the hierarchical decomposition of MEDS, there are temporal constraints of MTs that are performed by a finite set of overlapping actors (i.e., systems) while maintaining the logical sequencing of MTs deemed to accomplish a given mission. The temporal constraints and the logical sequencing of independent entities, which are typically domain-dependent, are semantically captured in the DSL. This step converts these semantics into a formal mathematical logic that represent an SoS configuration for accomplishing the mission objectives within the MW.

Mathematically, the MEDS can be represented by leveraging set-based design (SBD) principles [42] and the corresponding set-based mathematical notation. SBD is a concurrent complex system design methodology, which focuses on developing design alternatives by considering a set of design options at each hierarchical level that remains interlinked to design options at another hierarchical level [43]. While the SBD provides a spatially interlocked hierarchy for the MEDS, it does not address the temporal constraints and sequencing of the MTs. For this purpose, we pair set-based notation with AIA, which provides 13 temporal intervals for logical sequencing of MTs and accounts for temporal constraints [12].

Consider, for example, an arbitrary MEDS,  $\Omega_z = \{\mathcal{M}_{1z}, \mathcal{M}_{2z}\}$ , where  $\mathcal{M}_{1z}$  requires the following sequence of MTs to be completed,  $MT_1, MT_2, MT_3$ , in the specified order; and the available actors are three systems,  $S_a, S_b, S_c$ . Furthermore, it is reasonable to expect that each actor has unique abilities that limit what tasks an actor may perform and which actors can communicate with one another. Similarly, the tasks have their requirements as well, e.g., how long a task needs to be completed for or other sequencing details, such as prerequisite or parallel tasks. All such information is fully specified in the DSL.

For simplicity, assume  $S_a$  can perform  $MT_1$  or  $MT_2$ ;  $S_b$  can perform  $MT_2$  or  $MT_3$ ; and  $S_c$  can only perform  $MT_3$ . Moreover, let  $t_a, t_b$ , and,  $t_c$  be the time available from each actor to perform a task and  $t_1, t_2$ , and,  $t_3$  be the time required to complete the three tasks, respectively.

1) *Identifying MPs*: An MP is defined as a set of allocations of actors to MTs to accomplish the mission objectives. While determining all possible allocations is simply a constrained combinatoric problem based on what actors can perform, which tasks, ensuring their feasibility for accomplishing the mission requires that associated actor and task properties from DSL are considered as constraints when forming the MPs.

We propose utilizing first-order and temporal logic expressions, along with AIA to determine the feasibility of MPs. AIA enables construction of a logically consistent sequence of MTs by providing a set of 13 relations over a temporal interval [12], [44]. These 13 relationship—which are pair-wise disjoint and collectively exhaustive to represent a temporal interval—are: “meets ( $m$ ), before ( $<$ ), starts ( $s$ ), finishes ( $f$ ), overlaps ( $o$ ), during ( $d$ ), [and their inverses are]: met by ( $mi$ ), after ( $>$ ), started by ( $si$ ), finished by ( $fi$ ), overlapped by ( $oi$ ), contains ( $di$ ), and equality ( $=$ ).”

Based on AIA,  $\mathcal{M}_{1z}$  can be expressed as a partially ordered temporal sentence with AIA: “ $T_{\mathcal{M}_{1z}} = \text{MT}_1 m \text{MT}_2 m \text{MT}_3$ ,” which reads  $\mathcal{M}_{1z}$  requires  $\text{MT}_1$  meets  $\text{MT}_2$  meets  $\text{MT}_3$ . A number of logical proposition statements regarding  $\mathcal{M}_{1z}$  can be derived from the temporal sentence above, e.g.,  $\{\text{MT}_1 < \text{MT}_3; \mathcal{M}_{1z} : t\}$  or  $\{\text{MT}_2 d \text{MT}_3; \mathcal{M}_{1z} : f\}$  (i.e.,  $\text{MT}_1$  happens before  $\text{MT}_3$  is true for  $\mathcal{M}_{1z}$ , whereas  $\text{MT}_2$  happens during  $\text{MT}_3$  is false). Any false logical proposition statement implies that a mission objective cannot be achieved.

To mathematically represent the allocation of tasks to actors, we use the notation  $y \Leftarrow x$  implying that  $y$  performs  $x$ . We propose Algorithm 1 to identify multiple feasible MPs to complete a given mission, which utilizes the abovementioned notation along with AIA and first-order logic.

In order to illustrate a simple application of Algorithm 1 to  $\mathcal{M}_{1z}$ , consider the partially ordered temporal sentence (step 1):  $T_{\mathcal{M}_{1z}} = M_1 m M_2 m M_3$ . The action-task matrix (step 2) is given by:  $\text{ATM}_{\mathcal{M}_{1z}} = \begin{bmatrix} 1 & 1 & 0 \\ 0 & 1 & 1 \\ 0 & 0 & 1 \end{bmatrix}$  (this is based on which systems can perform what tasks as defined earlier). From this action-task matrix, a number of possible paths can be derived (step 3) along with their corresponding temporal sentences. For example

$$\text{MP}_{1\mathcal{M}_{1z}} = \{(S_a \Leftarrow \text{MT}_1), (S_b \Leftarrow \text{MT}_2), (S_b \Leftarrow \text{MT}_3)\}$$

$$T_{1\text{MP}_{1\mathcal{M}_{1z}}} = M_1 m M_2 m M_3$$

$$\text{MP}_{2\mathcal{M}_{1z}} = \{(S_a \Leftarrow \text{MT}_1, \text{MT}_2), (S_b \Leftarrow \text{MT}_3)\}$$

$$T_{2\text{MP}_{1\mathcal{M}_{1z}}} = M_1 d M_2 m M_3$$

⋮

Finally, the MP feasibility (step 4–1) is determined with a logical “and operation” between the temporal sentences  $T_{\mathcal{M}_{1z}}$ ,  $T_{1\text{MP}_{1\mathcal{M}_{1z}}}$ , and  $T_{2\text{MP}_{1\mathcal{M}_{1z}}}$ . Here,  $\{T_{\mathcal{M}_{1z}} \cap T_{1\text{MP}_{1\mathcal{M}_{1z}}} : t\}$  but  $\{T_{\mathcal{M}_{1z}} \cap T_{2\text{MP}_{1\mathcal{M}_{1z}}} : f\}$ . Hence,  $\text{MP}_{1\mathcal{M}_{1z}}$  is feasible and  $\text{MP}_{2\mathcal{M}_{1z}}$  is not.

2) *Feasible Mission Paths to MN*: An MN is a set of all feasible mission paths available to accomplish a given mission

#### --- **Algorithm 1:** Identify Feasible Mission Paths (Feasible MPs Algorithm). ---

Step 1: Construct a partially ordered temporal sentence ( $T$ ) using thirteen temporal intervals from AIA for MTs required for  $\mathcal{M}_i$  based on the MC

Step 2: Let  $y$  be the total number of Actors ( $A$ ) and  $n$  be the number of mission tasks ( $MT$ ) required for  $\mathcal{M}_i$

Build Actor-Task Matrix ( $ATM$ ) based on the following

```
for  $k = 1$  to  $y$  do
  for  $j = 1$  to  $n$  do
     $ATM(k, j) = \begin{cases} 1 & \text{if } A_k \text{ can perform } MT_j \\ 0 & \text{if } A_k \text{ can not perform } MT_j \end{cases}$ 
  end
end
```

**end** // Note:  $ATM$  is  $y \times n$  matrix

Step 3: Determine all possible complete and unique MPs to accomplish  $\mathcal{M}_i$  from the  $ATM$

A complete MP is where each MT is allocated to an actor (i.e.,  $\{A_k \Leftarrow MT_m \iff ATM(k, m) = 1\}$

where  $\iff$  denotes 'if and only if'

Step 4: Determine Feasibility of Mission Paths

**for** Each Mission Path  $MP_t$  **do**

- 1) Construct a logical sentence using thirteen temporal intervals from AIA for  $MP_t$  and compare to the logical sentence constructed in Step 1 for  $\mathcal{M}_i$ . If the ‘logical and operation’ for  $MP_t$  and  $\mathcal{M}_i$  sentences is false,  $MP_t$  is infeasible for  $\mathcal{M}_i$ .
- 2) Check time available property for each actor and the time required to complete all allocated tasks to that actor in  $MP_t$ ; if time available by an actor is less than time required for any actor;  $MP_t$  is infeasible for  $\mathcal{M}_i$ .
- 3) Perform validity checks for any other Actor-Task constraints specified in the DSL; if any constraints is invalid;  $MP_t$  is infeasible for  $\mathcal{M}_i$ .

**end**

---

$\mathcal{M}_i$ . Essentially, an MN describes the various pathways an SoS can be brought together for achieving a mission. An MN for  $\mathcal{M}_i$  is created by omitting infeasible MPs determined by the Algorithm 1 and given is by the following equation:

$$\mathcal{MN}_{\mathcal{M}_i} = \{\text{MP}_{1\mathcal{M}_i}, \text{MP}_{2\mathcal{M}_i}, \dots, \text{MP}_{t\mathcal{M}_i}\} \quad (1)$$

where  $\text{MP}_{1\mathcal{M}_i}, \dots, \text{MP}_{t\mathcal{M}_i}$  are all the feasible for  $\mathcal{M}_i$ .

3) *From MN to MW*: An MW is composed of a super set of MNs to accomplish all the missions defined in the MEDS (i.e.,  $\Omega_{\text{MEDS}}$ ). Mathematically, an MW is a one-to-one and an onto map—known as a bijection in set theory [45]—which is defined as a function given in (2) such that both condition in (3) hold true

$$\mathcal{MW} : \mathcal{MN} \rightarrow \Omega_{\text{MEDS}} \quad (2)$$

$$\forall \mathcal{M}_i \in \Omega_{\text{MEDS}} \exists \mathcal{MN}_i \in \mathcal{MN} | \mathcal{M}_i = \mathcal{MW}$$

$$\forall \mathcal{MN}_i, \mathcal{MN}_j \in \mathcal{MN}, i \neq j \Rightarrow \mathcal{MW}(\mathcal{MN}_i) \neq \mathcal{MW}(\mathcal{MN}_j). \quad (3)$$

In set-based notation, an MW for the MEDS assuming  $m$  total missions can then be represented by the following equation:

$$\mathcal{MW} = \{\mathcal{NM}_1, \dots, \mathcal{NM}_m\}. \quad (4)$$

The MEDS described by (4) provides a set-based decomposition that is interlinked from MN to all feasible MPs, via (1).

### C. Analytical Formalism

The major contribution of the previous section is to distill the MEDS from a high-level operational concept (e.g., OV-1) to feasible and realizable SoS configurations that can accomplish a given set of missions in the MW. Equation (1), for example, contains all the feasible MPs for mission  $\mathcal{M}_i$ . Each of the paths—which represent a unique SoS configuration in terms of system task allocation—will have a different performance for accomplishing the task. The purpose for this section is to present analytical methods that can be employed to evaluate the performance attributes for accomplishing the mission. It is important to note that the metrics for such evaluation are expected to be domain-specific and can include other qualities, attributes, and system utilities [46], in addition to the performance. Nevertheless, the underlying methodology remains similar, given the common mathematical formulation for representing the MEDS.

The set-based notation for MEDS, provided in (1) and (2) lends application of the various analytical methods that have been proposed in the SE literature. Dullen et al. [47] have provided a comprehensive review of such analytical methods that can be applied when a problem design can be represented in the set-based notation. Similarly, other researchers have proposed a number of analytical methods for SoS analysis, such as graph theory, design of experiments, and multiutility attribute theory, to name a few. A prerequisite of these methods is a given SoS configuration, which in the case of MEDS is established by the set-based mathematical notation provided in the previous section. While a comprehensive review of applying various set-based and SoS analytical methods to MEDS—which largely depends on the questions the decision-makers want to inquire—is beyond the scope of this article, the next section highlights how such methods can be applied to perform evaluation of the MEDS.

## V. ME FRAMEWORK APPLICATION EXAMPLE

This section provides an illustrative application of the proposed framework developed with a simple and notional sense-decide-effect example that can be generically applied from C2 missions to large-scale Internet of Things problems. The objective is to bring together SoS capabilities with certain constraints, in order to generate an MW against objects of interest, and provide feasible MPs that are ranked from best to worst in their performance to accomplish the mission.

### A. Sense-Decide-Effect ME Problem Space

The MEDS here is described by a set of five platforms that can perform a combination of sensing, deciding, effecting tasks on five different objects. Hence, each mission requires three MTs to be completed forming the following MC:

![Network diagram: Component interaction network diagram with platform, sensor, decider, effector, and object components.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/78d5774278a3f4a614f8c0ae485ce8d9_img.jpg)

E1  
E2  
E3  
D1  
D2  
S2  
S3  
S1  
P4  
P5  
P1  
P2  
P3  
Legend  
Platform component  
Sensor component  
Decider component  
Effector component  
Object component

```
graph LR
  E1[E1] --> E2[E2]
  E1 --> E3[E3]
  E2 --> E3
  D1[D1] --> E1
  D1 --> E2
  D1 --> E3
  D2[D2] --> E1
  D2 --> E2
  D2 --> E3
  S2[S2] --> E1
  S2 --> E2
  S2 --> E3
  S3[S3] --> E1
  S3 --> E2
  S3 --> E3
  S1[S1] --> E1
  S1 --> E2
  S1 --> E3
  P4[P4] --> D1
  P5[P5] --> D1
  P1[P1] --> D2
  P2[P2] --> D2
  P3[P3] --> D2
```

A network diagram showing directed connections between various component types: platform (hexagons), sensor (triangles), decider (circles), effector (squares), and object (circles), with a color-coded legend on the right.

Network diagram: Component interaction network diagram with platform, sensor, decider, effector, and object components.

Fig. 4. Operational concept representation of all platforms to create all potential MPs. Note platforms have different abilities to sense, decide, and effect.

![UML diagram: UML class diagram of a scenario model with objects, sensor, platform, and effector.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/4ba34b7c8f0b8799dc89462e0c71c52c_img.jpg)

S2  
S1  
D2  
O4  
O5  
S3  
D1  
objects  
sensor  
decider  
O3  
P5  
O2  
+  
objectives\_scen  
ario  
platform  
P4  
O1  
P3  
E3  
effector  
P1  
P2  
E2  
E1

```
classDiagram
    S2 --|> sensor
    S1 --|> sensor
    D1 --|> decider
    D2 --|> decider
    O4 --|> objects
    O5 --|> objects
    O3 --|> objects
    O2 --|> objects
    O1 --|> objects
    S3 --|> sensor
    objectives_scenario --|> platform
    objectives_scenario --|> effector
    sensor --|> platform
    sensor --|> decider
    platform --|> effector
    platform --|> decider
    P5 --|> platform
    P4 --|> platform
    P3 --|> platform
    P2 --|> platform
    P1 --|> effector
    E1 --|> effector
    E2 --|> effector
    E3 --|> effector
```

A UML class diagram showing a scenario class 'objectives\_scenario' with subclasses 'objects', 'sensor', 'platform', and 'effector', each inheriting from specialized diamond-shaped classes.

UML diagram: UML class diagram of a scenario model with objects, sensor, platform, and effector.

Fig. 5. Ontology structure with platform, object, sensor, decider, and effector individuals from Protege with their respective object property relations.

$\text{MC}_{\text{SDE}} = \{\text{MT}_S, \text{MT}_D, \text{MT}_E\}$ , where  $\text{MT}_S$  refers to sensing an object of interest,  $\text{MT}_D$  refers to deciding to act,  $\text{MT}_E$  refers to creating an effect. The set of systems that can accomplish one or more of these tasks, but not all, are referred to as platforms, where  $S = \{P_1, P_2, P_3, P_4, P_5\}$ . Collectively, they need to perform the sense-decide-effect mission on the objects,  $O = \{O_1, O_2, O_3, O_4, O_5\}$ . Fig. 4 shows the operational concept of the MEDS.

### B. ME Framework Application

1) *Simple DSL*: The first step is to comprehensively specify the MEDS with the DSL. The DSL here describes the task requirements, platform abilities, and the relationship between them and includes which platforms can perform what tasks and what are expected performance of each platform to perform a corresponding task. This information is critical in building the feasible MPs and subsequently evaluating their performance to complete the mission. The DSL and the corresponding ontology of the sense-decide-effect MEDS is built in Protégé (an open source ontology editor [48]) and illustrated in Fig. 5. Furthermore, Table II shows two notional metrics, probability of success for sense-decide-effect tasks as  $P_S, P_D, P_E$  and time to complete each task as  $T_S, T_D$ , and  $T_E$ , respectively (x denotes that the platform cannot perform the task). It is important to note that for brevity purposes, it is assumed that all platform metrics are uniformly applicable to all objects. In real-world application, it is expected that platform metrics will be objective-specific. Another important observation to note is that the values in

TABLE II  
PLATFORM METRICS SPECIFIED IN THE DSL

| Platform | Sense |       | Decide |       | Act   |       |
|----------|-------|-------|--------|-------|-------|-------|
|          | $P_S$ | $T_S$ | $P_D$  | $T_D$ | $P_E$ | $T_E$ |
| P1       | 0.95  | 3     | x      | x     | 0.88  | 5     |
| P2       | x     | x     | 1.00   | 17    | 0.92  | 6     |
| P3       | 0.91  | 4     | x      | x     | x     | x     |
| P4       | 0.88  | 2     | 1.00   | 16    | x     | x     |
| P5       | x     | x     | x      | x     | 0.91  | 4     |

Table II are fully encapsulated within the DSL as parameters for machine readability, and only represented here in the tabular form for human readability.

From an implementation stand-point, the individual DSL parameters of the platforms and mission objectives are specified in the form of .txt files, which can then be imported in Protégé to build the RDF compliant ontology. This ontology can then be queried and reasoned over from Python using “owlready2,” an ontology reasoning package [49], [50], where the mathematical formulation, Algorithm 1, and the suggested analytical techniques are implemented.

2) *MPs, Nets, and Web for Sense-Decide-Effect*: Next step in the MEDS formulation is to identify feasible MPs for bringing different SoS configurations together using the DSL. This can be obtained from the steps outlined in Algorithm 1.

1) With AIA, let  $\mathcal{T}_{\text{SDE}} = \{\text{MT}_S < \text{MT}_D < \text{MT}_E\}$  be the partially ordered temporal sentence for completing the mission ( $\mathcal{M}_{\text{SDE}}$ ) for any objective described in the set  $O$ . This sentence reads that  $\text{MT}_S$  happens before  $\text{MT}_D$ , and  $\text{MT}_D$  happens before  $\text{MT}_E$ .

2) The ATM is given by  $\text{ATM}_{\mathcal{M}_{\text{SDE}}} = \begin{bmatrix} 1 & 0 & 1 \\ 0 & 1 & 1 \\ 1 & 0 & 0 \\ 1 & 1 & 0 \\ 0 & 0 & 1 \end{bmatrix}$ . This reads

that  $P_1$  can sense and effect,  $P_2$  decide and effect,  $P_3$  can only sense,  $P_4$  can sense and decide, and  $P_5$  can only effect.

3) All possible sequential MPs can be identified from the abovementioned matrix to complete the  $\text{MC}_{\text{SDE}}$  with platform and task allocation. For example, consider the two possible but not necessarily feasible MPs, as feasibility is determined in the next step:  $\text{MP}_{\text{SDE}-1} = \{(P_1 \Leftarrow \text{MT}_S), (P_4 \Leftarrow \text{MT}_D), (P_2 \Leftarrow \text{MT}_E)\}$  and  $\text{MP}_{\text{SDE}-n} = \{(P_2 \Leftarrow \text{MT}_D), (P_1 \Leftarrow \text{MT}_S), (P_5 \Leftarrow \text{MT}_E)\}$ .

4) The feasibility of all possible MPs is evaluated by logically evaluating the partially ordered temporal sentence for each MP against the  $\mathcal{T}_{\text{SDE}}$  to complete the  $\text{MC}_{\text{SDE}}$ . For example, the partially ordered temporal sentence for  $\text{MP}_{\text{SDE}-1}$  and  $\text{MP}_{\text{SDE}-n}$  are given by:  $\mathcal{T}_{\text{MP}_{\text{SDE}-1}} = \{\text{MT}_S < \text{MT}_D < \text{MT}_E\}$  and  $\mathcal{T}_{\text{MP}_{\text{SDE}-n}} = \{\text{MT}_D < \text{MT}_S < \text{MT}_E\}$ , respectively. Here, the logical proposition  $\{\mathcal{T}_{\text{SDE}} \cap \mathcal{T}_{\text{MP}_{\text{SDE}-1}} : t\}$  while  $\{\mathcal{T}_{\text{SDE}} \cap \mathcal{T}_{\text{MP}_{\text{SDE}-n}} : f\}$ . Hence,  $\text{MP}_{\text{SDE}-1}$  is feasible while  $\text{MP}_{\text{SDE}-n}$  is not.

Using Algorithm 1, a total of 18 feasible MPs are identified for each object in set  $O$ , hence, the MN for each object is given by:  $\mathcal{MN}_{\text{SDE}} = \{\text{MP}_1, \text{MP}_2, \text{MP}_3, \dots, \text{MP}_{18}\}$ . The

TABLE III  
MN OF MPs FOR OBJECT #1

| ID | Sense | Decide | Act | Mission Success (%) | Time(s) |
|----|-------|--------|-----|---------------------|---------|
| 1  | P1    | P4     | P2  | 0.874               | 25      |
| 2  | P1    | P2     | P2  | 0.874               | 26      |
| 3  | P1    | P4     | P5  | 0.864               | 23      |
| 4  | P1    | P2     | P5  | 0.864               | 24      |
| 5  | P3    | P4     | P2  | 0.837               | 26      |
| 6  | P3    | P2     | P2  | 0.837               | 27      |
| 7  | P1    | P4     | P1  | 0.836               | 24      |
| 8  | P1    | P2     | P1  | 0.836               | 25      |
| 9  | P3    | P4     | P5  | 0.828               | 24      |
| 10 | P3    | P2     | P5  | 0.828               | 25      |
| 11 | P4    | P4     | P2  | 0.810               | 24      |
| 12 | P4    | P2     | P2  | 0.810               | 25      |
| 13 | P4    | P4     | P5  | 0.801               | 22      |
| 14 | P4    | P2     | P5  | 0.801               | 23      |
| 15 | P3    | P4     | P1  | 0.801               | 25      |
| 16 | P3    | P2     | P1  | 0.801               | 26      |
| 17 | P4    | P4     | P1  | 0.774               | 23      |
| 18 | P4    | P2     | P1  | 0.774               | 24      |

![Network diagram: Network diagram of object sensing, information sent, and action instructions followed among nodes.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/ef7a88e04d1939ee09bafd5c3072adf8_img.jpg)

P4  
P5  
P3  
O1  
P1  
P2  
Legend  
Object Sensed  
Sense Information Sent  
Decision Information Sent  
Action Instructions Followed

```
graph LR
  P4((P4)) -->|Object Sensed| P4
  P4 -->|Sense Information Sent| P3((P3))
  P4 -->|Sense Information Sent| P2((P2))
  P4 -->|Decision Information Sent| P1((P1))
  P5((P5)) -->|Object Sensed| P1
  P5 -->|Sense Information Sent| O1((O1))
  P5 -->|Decision Information Sent| P2
  P3 -->|Object Sensed| O1
  P3 -->|Sense Information Sent| P2
  P3 -->|Decision Information Sent| P1
  P2 -->|Object Sensed| P2
  P2 -->|Sense Information Sent| O1
  P2 -->|Decision Information Sent| P1
  P1 -->|Action Instructions Followed| O1
```

A network diagram showing interactions between a central red node O1 and five peripheral purple nodes (P1 to P5), with directed arrows indicating Object Sensed, Sense Information Sent, Decision Information Sent, and Action Instructions Followed.

Network diagram: Network diagram of object sensing, information sent, and action instructions followed among nodes.

Fig. 6. Graph-based visualization of the MN for object, O1.

![Network diagram: Comparison of object sensing, sense information, decision information, and action instructions between two states.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/6f119d066b5e51370df585ce69c94fb4_img.jpg)

(a)  
(b)  
Legend  
Object Sensed  
Sense Information Sent  
Decision Information Sent  
Action Instructions Followed  
P2  
P4  
O1  
P1  
P2  
O2  
P1

```
graph LR
  subgraph a ["(a)"]
    P4 -->|Object Sensed| P2
    P2 -->|Action Instructions Followed| O1
    O1 -->|Sense Information Sent| P1
  end
  subgraph b ["(b)"]
    P2 -->|Action Instructions Followed| O2
    O2 -->|Sense Information Sent| P1
    P1 -->|Decision Information Sent| P2
    P2 -->|Object Sensed| P2
  end
```

Two diagrams, (a) and (b), show interactions among nodes P1, P2, P4, and objects O1 and O2, with a legend defining the four types of directed edges.

Network diagram: Comparison of object sensing, sense information, decision information, and action instructions between two states.

Fig. 7. Graph theory visualization of the potentially best MPs for objects “O1” and “O2,” depicted in (a) and (b) respectfully.

corresponding platform-task allocation for these MPs in provided in Table III. All 5 MNs create one single MW given by  $\mathcal{MW} = \{\mathcal{MN}_1, \mathcal{MN}_2, \mathcal{MN}_3, \mathcal{MN}_4, \mathcal{MN}_5\}$  and contains a total of 90 MPs.

3) *ME Analytical Analysis for Sense-Decide-Effect*: A number of SoS analytical methods can now be employed to obtain performance analysis of the resulting MPs, MN, and MW for  $\mathcal{M}_{\text{SDE}}$ . For an example, the total probability of mission success from each MP can be obtained as  $P_{\mathcal{M}_{\text{SDE}}} = P_S P_D P_E$  (assuming independence between these probabilities), and the total time to accomplish the mission can be obtained as  $T_{\mathcal{M}_{\text{SDE}}} = T_S + T_D + T_E$ . These values for each MP are provided in Table III.

Graph theoretic formulation for MPs and MNs can also be obtained by considering the platforms as graph nodes and the MTs as the graph edges that connect the nodes. Fig. 6 illustrates the entire MN for  $O_1$ , while Fig. 7 shows two individual MPs

TABLE IV  
UTILITY SCORES FOR EACH PLATFORM

| Rank | Platform | Utility Score |
|------|----------|---------------|
| 1    | P2       | 2.833         |
| 2    | P4       | 2.573         |
| 3    | P1       | 2.179         |
| 4    | P5       | 1.446         |
| 5    | P3       | 1.186         |

for  $O_1$  and  $O_2$ . In addition to providing a visual illustration of MPs and MNs, the underlying graph formulation also enables application of graph-based SoS analytical methods to the ME problem space.

Furthermore, the criticality or utility of each platform in the MW can be obtained by employing multiattribute utility theory or weighted-objectives methods. Table IV lists a rank-ordered utility of different platforms, which is calculated based on the MTs a platform can perform and the criticality of the platform in forming different MPs. Specifically, the utility score presented in Table IV is calculated using summation of normalized page rank measurement, normalized degree centrality measurement, and the fraction of a platforms ability to sense, decide, and effect, among other platforms in MT. Page rank [51] computes a ranking of the nodes in the graph based on the structure of the incoming links, while the degree centrality [52] computes the fraction of nodes, a node is connected with.

It is important to note that the analysis presented here is to show a proof-of-concept of applying various SoS analytical methods to the distilled MEDS with MPs, MNs, and MW. The application of these methods is directly dependent on the question of interest that a decision-maker or an operational analyst seeks to uncover from the MEDS and remains application domain-specific. In future work, we plan to expand the application of SoS analytical methods to a real-world MEDS identifying a mapping between question of interest and SoS analytical methods, and then demonstrating its application to MEDS.

## VI. CONCLUSION

ME leverages a dynamic, flexible, and near real-time configuration of SoS to accomplish one or more missions. The underlying challenge for ME is to distill and analyze a large design-space of integrating multiple complex systems where there is a combinatoric explosion of possible interactions in the systems and an inherent ambiguity in the description of capabilities and parameters due to their multidisciplinary nature. In this work, we have proposed a systemic ME framework to determine mission accomplishment pathways from a very large design space to a manageable set of SoS configurations capable of successfully completing the mission. This framework began by first identifying a mission-focused ontology and the DSL, which is then utilized with SBD principles and AIA to form feasible MPs, MN, and MW. These MPs, MN, and MW are then evaluated by SoS analytical methods for performance analysis of completing the mission objectives and assess vulnerabilities.

The framework and component algorithms described in this article provide multidisciplinary foundations to enable transition of ME concept into practical SoS applications. However, more research and development is needed in the three foundational pillars of the proposed framework. In the ontological foundation, a critical area for future research is in the adoption of upper ontologies, such as the basic formal ontology, dublin core, common core, and unified formal ontology, etc. As the scope of the SoS under consideration expands, an integrated set of consistent upper ontologies, accompanied by a canonical controlled vocabulary, will become increasingly critical. The scalability of the mathematical foundation into real-time practical applications will also need to be examined. Finally, analytical formalism that incorporates an incentive structure to encourage voluntary system participation in collaborative and virtual SoS types will need to be researched. In the future, we will focus on identifying a real-world formulation of MEDS, soliciting the analytical questions and performance attributes decision-makers and operation-analysts seek to address and demonstrate how they can be addressed by the framework proposed in this article.

## ACKNOWLEDGMENT

The views, opinions, and/or findings expressed are those of the authors and should not be interpreted as representing the official views or policies of the Department of Defense or the U.S. Government. Distribution Statement A: Approved for Public Release, Distribution Unlimited.

## REFERENCES

- [1] Y. Bar-Yam, *Making Things Work: Solving Complex Problems in a Complex World*, 1st ed. Cambridge, MA, USA: Knowledge Press, Jan. 2004.
- [2] M. W. Maier, "Architecting principles for systems-of-systems," *Syst. Eng.*, vol. 1, no. 4, pp. 267–284, 1998.
- [3] S. Deller, S. Bowling, G. Rabadi, A. Tolk, and M. Bell, "Applying the information age combat model: Quantitative analysis of network centric operations," *Int. C2 J.*, vol. 3, no. 1, pp. 1–25, Jan. 2009. [Online]. Available: [https://digitalcommons.odu.edu/msve\\_fac\\_pubs/28](https://digitalcommons.odu.edu/msve_fac_pubs/28)
- [4] A. K. Raz, C. R. Kenley, and D. A. DeLaurentis, "A system-of-systems perspective for information fusion system design and evaluation," *Inf. Fusion*, vol. 35, pp. 148–165, May 2017.
- [5] J. E. Trainor and T. Subbio, "Critical issues in disaster science and management: A dialogue between researchers and practitioners," *FEMA Higher Educ. Project*, 2014. [Online]. Available: <http://udspace.udel.edu/handle/19716/13418>
- [6] C. Fan and A. Mostafavi, "Metanetwork framework for performance analysis of disaster management system-of-systems," *IEEE Syst. J.*, vol. 14, no. 1, pp. 1265–1276, Mar. 2020. [Online]. Available: <https://ieeexplore.ieee.org/document/8765590>
- [7] A. Gorod, B. E. White, V. Ireland, S. J. Gandhi, and B. Sauser, Eds., *Case Stud. in Syst. of Syst., Enterprise Syst., and Complex Syst. Eng.*. Boca Raton, FL, USA: CRC Press, Jul. 2014, doi: 10.1201/b17139.
- [8] J. Klein and H. Van Vliet, "A systematic review of system-of-systems architecture research," in *Proc. 9th Int. ACM Sigsoft Conf. Qual. Softw. Architectures*, Jun. 2013, pp. 13–22.
- [9] A. Tolk, P. Barry, and S. C. Doskey, "Using modeling and simulation and artificial intelligence to improve complex adaptive systems engineering," *Int. J. Model., Simul., Sci. Comput.*, vol. 13, no. 2, Apr. 2022, Art. no. 2241004, doi: 10.1142/S1793962322410045.
- [10] Z. Fang, "System-of-systems architecture selection: A survey of issues, methods, and opportunities," *IEEE Syst. J.*, vol. 16, no. 3, pp. 4768–4779, Sep. 2022. [Online]. Available: <https://ieeexplore.ieee.org/document/9593274>

- [11] D. of Defense, "Mission engineering guide," Office Under Secretary Defense Res. Eng., Washington, DC, USA, Tech. Rep., Nov. 2020.
- [12] J. F. Allen, "Maintaining knowledge about temporal intervals," *Commun. ACM*, vol. 26, no. 11, pp. 832–843, Nov. 1983, doi: [10.1145/182.358434](https://doi.org/10.1145/182.358434).
- [13] J. H. Friedman and L. C. Rafsky, "Graph-theoretic measures of multivariate association and prediction," *Ann. Statist.*, vol. 11, no. 2, pp. 377–391, Jun. 1983.
- [14] R. L. Keeney and H. Raiffa, *Decisions With Multiple Objectives: Preferences and Value Trade-Offs*. Cambridge, MA, USA: Cambridge Univ. Press, 1993.
- [15] M. Velasquez and P. T. Hester, "An analysis of multi-criteria decision making methods," 2013. [Online]. Available: <https://www.semanticscholar.org/paper/An-Analysis-of-Multi-Criteria-Decision-Making-Velasquez-Hester/4587b03bd27760ac5f5e5f16196d4b4c8c462bec>
- [16] I. G. Vargas and R. T. V. Braga, "Understanding system of systems management: A systematic review and key concepts," *IEEE Syst. J.*, vol. 16, no. 1, pp. 510–519, Mar. 2022. [Online]. Available: <https://ieeexplore.ieee.org/document/9187218>
- [17] SEBoK, "Mission engineering—SEBoK," 2021. [Online]. Available: [https://sebokwiki.org/w/index.php?title=Mission\\_Engineering&oldid=67286](https://sebokwiki.org/w/index.php?title=Mission_Engineering&oldid=67286)
- [18] R. Gold, *Mission Eng.*. Springfield, VA, USA: Nat. Defense Ind. Assoc., 2016.
- [19] D. L. Van Bossuyt, P. Beery, B. M. O'Halloran, A. Hernandez, and E. Paulo, "The naval postgraduate school's department of systems engineering approach to mission engineering education through capstone projects," *Systems*, vol. 7, no. 3, p. 38, Sep. 2019. [Online]. Available: <https://www.mdpi.com/2079-8954/7/3/38>
- [20] P. Ondrus and M. Fatig, "Mission engineering," Mar. 1993. [Online]. Available: <https://ntrs.nasa.gov/citations/19940019408>
- [21] A. Sousa-Poza, "Mission engineering," *Int. J. Syst. Syst. Eng.*, vol. 6, no. 3, pp. 161–185, Sep. 2015, doi: [10.1504/IJSSE.2015.071453](https://doi.org/10.1504/IJSSE.2015.071453).
- [22] J. Bricio-Neto, "DOD mission engineering and integration explorative-exploitative architecture for technology innovation," Doctoral Dissertation, Old Dominion Univ., Norfolk, VA, USA, Apr. 2020. [Online]. Available: [https://digitalcommons.odu.edu/emse\\_etds/175](https://digitalcommons.odu.edu/emse_etds/175)
- [23] P. Beery and E. Paulo, "Application of model-based systems engineering concepts to support mission engineering," *Systems*, vol. 7, no. 3, p. 44, Sep. 2019.
- [24] R. Cloutier, G. Muller, D. Verma, R. Nilchiani, E. Hole, and M. Bone, "The concept of reference architectures," *Syst. Eng.*, vol. 13, no. 1, pp. 14–27, 2010. [Online]. Available: <https://onlinelibrary.wiley.com/doi/abs/10.1002/sys.20129>
- [25] D. Kaslow, A. Levi, P. T. Cahill, B. Ayres, D. Hurst, and C. Croney, "Mission engineering and the CubeSat system reference model," in *Proc. IEEE Aerosp. Conf. (50100)*, Mar. 2021, pp. 1–8.
- [26] K. Giles and K. Giammarco, "A mission-based architecture for swarm unmanned systems," *Syst. Eng.*, vol. 22, no. 3, pp. 271–281, 2019.
- [27] E. B. K. Lee, D. L. Van Bossuyt, and J. F. Bickford, "Digital twin-enabled decision support in mission engineering and route planning," *Systems*, vol. 9, no. 4, p. 82, Dec. 2021.
- [28] G. De Zaiacomo, G. Blanco Arnao, R. Bunt, and D. Bonetti, "Mission engineering for the RETALT VTVL launcher," *CEAS Space J.*, vol. 14, no. 3, pp. 533–549, Jul. 2022.
- [29] A. S. Hernandez and A. G. Pollman, "Characterizing integration challenges in mission engineering to form solution strategies," *Syst. Eng.*, vol. 25, no. 4, pp. 404–418, 2022, doi: [10.1002/sys.21621](https://doi.org/10.1002/sys.21621).
- [30] J. B. Brown and E. V. Olinick, "A set covering approach for selecting preferred systems to support mission engineering," *IEEE Syst. J.*, vol. 17, no. 4, pp. 5616–5625, Dec. 2023.
- [31] A. Dachowicz et al., "Mission engineering and design using real-time strategy games: An explainable AI approach," *J. Mech. Des.*, vol. 144, no. 2, Nov. 2021, Art. no. 021710.
- [32] G. B. Benitez, N. F. Ayala, and A. G. Frank, "Industry 4.0 innovation ecosystems: An evolutionary perspective on value cocreation," *Int. J. Prod. Econ.*, vol. 228, Oct. 2020, Art. no. 107735.

- [33] "OV-1: High level operational concept graphic," 2024. [Online]. Available: [https://dodcio.defense.gov/Library/DoD-Architecture-Framework/dodaf20\\_ov1/](https://dodcio.defense.gov/Library/DoD-Architecture-Framework/dodaf20_ov1/)
- [34] C. Santos, "An adaptive kill web framework for mission engineering and concept exploration analysis," Marine Corps Univ., Quantico, VA, USA, Jun. 2002. [Online]. Available: <https://www.mors.org/Events/Symposium/Past-Symposiums/2022-90th-Symposium>
- [35] J. S. Dahmann and K. J. Baldwin, "Understanding the current state of US defense systems of systems and the implications for systems engineering," in *Proc. 2nd Annu. IEEE Syst. Conf.*, Apr. 2008, pp. 1–7. [Online]. Available: <https://ieeexplore.ieee.org/document/4518994>
- [36] R. Giachetti, S. Wangert, and R. Eldred, "Interoperability analysis method for mission-oriented system of systems engineering," in *Proc. IEEE Int. Syst. Conf.*, Apr. 2019, pp. 1–6.
- [37] A. Sutii, T. Verhoeff, and M. G. J. V. d. Brand, *Ontologies in Domain Specific Languages: A Systematic Literature Rev.* (Computer Science Reports). Eindhoven, The Netherlands: Technische Universiteit Eindhoven, 2014.
- [38] I. Winkler and T. C. Brown, "The kill chain," in *You CAN Stop Stupid: Stopping Losses From Accidental and Malicious Actions*. Hoboken, NJ, USA: Wiley, 2021, pp. 153–165. [Online]. Available: <https://ieeexplore.ieee.org/document/9822602>
- [39] D. DeLaurentis, *Understanding Transp. as a Syst.-of-Syst. Des. Problem*. Reston, VA, USA: Amer. Inst. Aeronaut. Astronaut., Jan. 2005, doi: [10.2514/6.2005-123](https://doi.org/10.2514/6.2005-123).
- [40] J. Z. Pan, "Resource description framework," in *International Handbooks on Information Systems*, S. Staab and R. Studer, Eds., New York, NY, USA: Springer, 2009, pp. 71–90.
- [41] I. Ceh, M. Črepinšek, T. Kosar, and M. Mernik, "Ontology driven development of domain-specific languages," *Comput. Sci. Inf. Syst.*, vol. 8, pp. 317–342, May 2011.
- [42] D. J. Singer, N. Doerry, and M. E. Buckley, "What is set-based design?," *Nav. Eng. J.*, vol. 121, no. 4, pp. 31–43, Oct. 2009.
- [43] N. Shallcross, G. S. Parnell, E. Pohl, and E. Specking, "Set-based design: The state-of-practice and research opportunities," *Syst. Eng.*, vol. 23, no. 5, pp. 557–578, 2020.
- [44] M. Grüninger and Z. Li, "The time ontology of Allen's interval algebra," in *Proc. 24th Int. Symp. Temporal Representation Reason.*, 2017, pp. 16:1–16:16. [Online]. Available: <http://drops.dagstuhl.de/opus/volltexte/2017/7927>
- [45] I. I. H. J. Cho and *Hemen Dutta, Concise Introduction to Logic and Set Theory*. Boca Raton, FL, USA: CRC Press, Sep. 2021.
- [46] O. L. de Weck, A. M. Ross, and D. H. Rhodes, "Investigating relationships and semantic sets amongst system lifecycle properties (Ilities)," in *Proc. 3rd Int. Eng. Syst. Symp.*, Jun. 2012, pp. 1–12. [Online]. Available: [https://seari.mit.edu/documents/preprints/DEWECK\\_CESUN12.pdf](https://seari.mit.edu/documents/preprints/DEWECK_CESUN12.pdf)
- [47] S. Dullen, D. Verma, M. Blackburn, and C. Whitcomb, "Survey on set-based design (SBD) quantitative methods," *Syst. Eng.*, vol. 24, no. 5, pp. 269–292, 2021.
- [48] "protégé," 2024. [Online]. Available: <https://protege.stanford.edu/>
- [49] J.-B. Lamy, "Owready: Ontology-oriented programming in Python with automatic classification and high level constructs for biomedical ontologies," *Artif. Intell. Med.*, vol. 80, pp. 11–28, Jul. 2017. [Online]. Available: <https://www.sciencedirect.com/science/article/pii/S0933365717300271>
- [50] "Welcome to Owready2's documentation!—Owready2 0.41 documentation," 2024. [Online]. Available: <https://owready2.readthedocs.io/en/v0.42/>
- [51] L. Page, S. Brin, R. Motwani, and T. Winograd, "The PageRank citation ranking: Bringing order to the web," Nov. 1999. [Online]. Available: <https://www.semanticscholar.org/paper/The-PageRank-Citation-Ranking-%3A-Bringing-Order-to-Page-Brin/eb82d3035849cd23578096462ba419b53198a556>
- [52] J. Zhang and Y. Luo, *Degree Centrality, Betweenness Centrality, and Closeness Centrality in Social Netw.*. Amsterdam, The Netherlands: Atlantis Press, Mar. 2017, pp. 300–303. [Online]. Available: <https://www.atlantis-press.com/proceedings/msam-17/25874733>

![Portrait of a man in a suit and checkered shirt.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/6d9013c24741e861f3c8e0a763b6da22_img.jpg)

Portrait of a man in a suit and checkered shirt.

**Ali K. Raz** (Senior Member, IEEE) received the B.Sc. and M.Sc. degrees in electrical engineering from Iowa State University, Ames, IA, USA, in 2005 and 2009, respectively, and the Ph.D. degree in aeronautics and astronautics from Purdue University, West Lafayette, IN, USA, in 2016.

He is currently an Assistant Professor with Systems Engineering and Operations Research Department, George Mason University (Mason), Fairfax, VA, USA, and an Assistant Director of Intelligent Systems and Integration, C5I Center. His research and teaching interests include understanding collaborative autonomy and developing systems engineering methodologies for integrating autonomous systems. Prior to joining Mason, he was a Visiting Assistant Professor with School of Aeronautics and Astronautics, Purdue University, West Lafayette, IN, USA, and he was with Naval Postgraduate School, John Hopkins University Applied Physics Laboratory (JHU-APL), Laurel, MD, USA, the United States Missile Defense Agency, USA, and Honeywell Aerospace.

Dr. Raz is the Chair of the Information Command-and-Control Systems Technical Committee of the American Institute for Aeronautics and Astronautics (AIAA) and a Co-Chair of International Council of Systems Engineering (INCOSE) Complex Systems Working Group. He is a Certified Systems Engineering Professional (CSEP) and a senior member of AIAA.

![Portrait of a man in a suit and tie, smiling.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/2de51a31da9b0ffd9d017f035d498997_img.jpg)

Portrait of a man in a suit and tie, smiling.

**Christopher Santos** received the B.Sc. degree in civil engineering from the University of Southern California, Los Angeles, CA, USA, in 1994, the Executive M.B.A degree in defense acquisition and program management from Naval Postgraduate School, Monterey, CA, USA, in 2004, the master's degree in military operational art and science from Air University, Montgomery, AL, USA, in 2005, and the M.Sc. degree in operations research from Naval Postgraduate School, Monterey, CA, USA, in 2016.

He is a Corporate Operations Research Analyst with the LinQuest Corporation (LinQuest), Los Angeles, CA, USA, and a Principal Investigator for the Defense Advanced Research Projects Agency (DARPA) Adaptive Warfighting Architectures project. He has an interest in infusing quantitative analysis techniques into traditionally qualitative planning and policy development processes. Prior to joining LinQuest, he served 25 years in the U.S. Navy, the first half as a Naval Aviator in the F/A-18 Hornet with three combat deployments across the globe, and the second half as an operations research analyst at the joint task force, combatant command, and service headquarters levels.

Mr. Santos is a member of the Military Operations Research Society (MORS) and the Institute for Operations Research and the Management Sciences (INFORMS).

![Portrait of a young man with glasses and a plaid shirt.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/475caf31ae90b878f12d651b689cc9d1_img.jpg)

Portrait of a young man with glasses and a plaid shirt.

**Mohammed Bhuyian** received the B.Sc. and M.Sc. degrees in bioengineering from George Mason University, Fairfax, VA, USA, in 2022 and 2023 respectively.

He is a Graduate Researcher with the Systems Engineering and Operations Research Department, George Mason University, and affiliate to the C5I Center. He is currently a Professional Systems Engineer. He has performed research in areas revolving around graph theory, temporal logic reasoning, and utility theory in the C5I Center, Groege Mason University.

![Portrait of a smiling man in a suit and green tie.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/44149aafc1d3d15757730b3d99bb0c42_img.jpg)

Portrait of a smiling man in a suit and green tie.

**Daniel Maxwell** received the B.S. degree in criminal justice from the Rochester Institute of Technology, Rochester, NY, USA, in 1979, the M.B.A. degree from Long Island University, Brooklyn, NY, USA, in 1984, and the Ph.D. degree in information technology (with emphasis in operations research) from George Mason University, Fairfax, VA, USA, in 1994.

He is the President of KaDSci, LLC, Fairfax, VA, USA, a veteran owned decision science and information science research and analysis company. Over a 30-year research career, he has completed a significant body of work and published in the areas of operations research, simulation, information age transformation, information and decision science, and artificial intelligence. He was with the U.S. Defense Science Board Task Force on Intelligence, the Board of Directors of the Military Operations Research Society, and multiple research organizations and maintains affiliate faculty status with George Mason University. Prior to becoming an operations research analyst, he served the first half of his Military career as a military police officer, completing Command and General Staff College, as well as Ranger & Airborne schools as part of his military training

Dr. Maxwell became a Fellow of the Military Operations Research Society (MORS) for his contributions to the state of the art and practice in the military operations research.

![Photo: Portrait of a man in a suit in front of an American flag.](fig/Conceptual_Mathematical_and_Analytical_Foundations_for_Mission_Engineering_and_System_of_Systems_Analysis/6e5c78a85b8088d4ab0ddcced8a67ca7_img.jpg)

A head-and-shoulders portrait of a man wearing a dark suit, white shirt, and patterned tie, positioned against a blue background with an American flag visible on the left.

Photo: Portrait of a man in a suit in front of an American flag.

**Jose L. Bricio-Neto** received the Bachelor of Science degree in mechanical engineering, the Master of Science degree in modeling and simulation, and Doctor of Philosophy degree from Old Dominion University, Norfolk, VA, USA, in 2002, 2009, and 2020, respectively.

He was a Program Manager with the Defense Advanced Research Projects Agency (DARPA), responsible for successfully executing complex program over 3 years with \$170 M DoD investment. In this position, he developed a Joint All Domain Analy-

sis Capability consisting of tools, processes, teams, and government-owned cloud infrastructure for large-scale scenario-based analyzes supporting concept exploration for technology investment decisions. Before this assignment, he was a Mission Engineering Advanced Capabilities Manager with OUSD A&S and International Cooperation Architect with the Navy International Programs office, leading digital transformation initiatives. He researched and published on mission engineering and integration, explorative and exploitative innovation, and modeling and simulation frameworks.