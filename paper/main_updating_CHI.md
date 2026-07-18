\ifdefined\PaperCameraReady
  \documentclass[sigconf]{acmart}
\else
  \documentclass[manuscript,review,anonymous]{acmart}
\fi
\settopmatter{printacmref=false}
\renewcommand\footnotetextcopyrightpermission[1]{} 
\pagestyle{plain} 
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage[utf8]{inputenc}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{float}
\usepackage{flafter}
\usepackage{booktabs}
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta}
\settopmatter{
  printacmref=false,
  printccs=false,
  printfolios=true
}
\renewcommand\footnotetextcopyrightpermission[1]{}
\fancyhead{} 
\renewcommand{\shortauthors}{}

\title{Dataset Design as Ontology Design: Representational Consequences of QA Segmentation in Personal AI Interaction Data}
\providecommand{\PaperAuthor}{Anonymous Author(s)}
\author{\PaperAuthor}

\begin{document}


% ================================================================
% ABSTRACT
% ================================================================

\begin{abstract}
Personalized AI systems increasingly rely on fine-tuning language
models on longitudinal interaction data.
The dominant practice converts this data into question--answer (QA)
pairs, thereby operationalizing interaction as locally independent query–response mappings rather than temporally structured processes.
We empirically test this assumption through a longitudinal case study
of a single three-year personal interaction corpus (1,122 sessions,
35,756 role-marked turns), constructing two parallel representations of the same
underlying data---a cognitive trajectory graph and QA-derived pair
sequences---and comparing their structural properties across six
controlled conditions.

We find that trajectory-based representations exhibit significantly
different transition dynamics from QA-derived ones (KS $D = 0.298$).
These differences persist under semantic reconstruction and when
evaluated over the full corpus.
An order-shuffled counterfactual further demonstrates that temporal
ordering---rather than content alone---accounts for the observed
structure (KS $D = 0.101$), ruling out content-level explanations
for the distributional divergence.

These results suggest that QA slicing removes explicit supervision 
for higher-order conditional dependencies by collapsing multi-step 
sequences into independent pairs. This structural consequence has 
direct implications for training data design in personal AI settings, 
where individual patterns are amplified rather than averaged out.
We provide a replicable pipeline and synthetic example data to
support analogous analyses on other corpora.
\end{abstract}
\keywords{personal AI, longitudinal interaction, dataset representation, QA segmentation, cognitive trajectories, data-centric AI}
\maketitle
\fancyhead{}
% ================================================================
\section{Introduction}

As large language models become embedded in long-term knowledge work,
a tension has emerged between two conceptions of AI continuity.
Existing systems increasingly incorporate forms of cross-session memory: storing facts, tracking preferences, and retrieving past interactions~\cite{kim2026spring,
memgpt, park2023generative}.
These mechanisms address \emph{informational} continuity---the system
remembers what was said.

However, informational continuity differs from \emph{cognitive} continuity.
When a user engages with an AI system over months or years, they are not
simply issuing independent queries. They are refining ideas, revising
assumptions, and building understanding through iterative exchange.
If this process constitutes a form of cognitive trajectory, then the
question is not only what the system retains, but whether the structure
of evolving thought can be preserved---and eventually learned from.

Recent work has begun to examine how AI systems reshape human cognitive
processes through iterative interaction loops~\cite{kittur2025tools}.
However, existing research has largely focused on interaction-level effects
rather than the underlying representational structure of cognition
itself---leaving open the question of whether human thought is better
modeled as a trajectory than as a static mapping.

% ---------------------------------------------------------------
\subsection*{The Representation Problem}
% ---------------------------------------------------------------

The dominant practice for fine-tuning personalized AI systems converts
interaction data into question--answer (QA) pairs: a user query followed
by a model response.
This represents a structural choice that encodes a prior assumption 
about the nature of reasoning: thought is locally conditioned, with 
each response as a function of the immediately preceding input.

Existing personalization systems (whether they update user-specific
adapters~\cite{kim2026spring}, manage long-term memory across
context tiers~\cite{memgpt}, or maintain experience
streams~\cite{park2023generative}) operate downstream of this representational assumption.
They optimize \emph{how} to use QA-formatted data, but do not question
whether that format adequately represents the cognitive processes it
purports to capture.

We argue that \textbf{dataset design is ontology design}: the choice of
how to segment interaction data encodes implicit assumptions about what
thinking \emph{is}.
For general-purpose AI trained at scale, these assumptions may average out.
For personal AI trained on hundreds of conversations from a single user,
every structural decision is amplified.

% ---------------------------------------------------------------
\subsection*{Hypothesis}
% ---------------------------------------------------------------

We formalize this tension as a distinction between two representations:

\begin{align}
\text{QA representation:} \quad
  & \textit{question} \;\longrightarrow\; \textit{answer}
    \label{eq:qa} \\[4pt]
\text{Trajectory representation:} \quad
  & \textit{state}_{t} \;\longrightarrow\; \textit{state}_{t+1}
    \label{eq:traj}
\end{align}

Under the QA view, each response is conditioned on the current query alone.
Under the trajectory view, each cognitive state is conditioned on the
accumulated history of reasoning---a higher-order dependency structure:

\begin{align}
P\!\left(x_{t+1} \mid x_{t}\right)
  &\qquad \text{[QA: approximates first-order dependency]}
  \label{eq:qa_markov} \\[4pt]
P\!\left(x_{t+1} \mid x_{t},\, x_{t-1},\, \ldots\right)
  &\qquad \text{[Trajectory: higher-order]}
  \label{eq:traj_higher}
\end{align}

This leads to a testable hypothesis: \emph{if real cognitive trajectories
encode higher-order, order-dependent structure, then QA-based
representations should exhibit systematic differences in their transition
dynamics---even when accounting for content and semantic similarity.}

We do not assume that QA representations are entirely incapable of
capturing such structure.
Rather, we ask whether they empirically do so, and what is lost when
they do not.

% ---------------------------------------------------------------
\subsection*{Study Design and Scope}
% ---------------------------------------------------------------

We adopt a longitudinal case study design, analyzing a single
three-year personal interaction corpus in depth.
This design reflects a deliberate methodological tradeoff: where
cross-sectional studies offer breadth across users, a longitudinal
case study enables the kind of depth---tracking structural properties
across thousands of sessions, controlling for individual cognitive
style, and observing evolution over years---that aggregate approaches
cannot achieve with personal AI data.
Case study methodology has an established role in HCI research for
developing theoretical frameworks and demonstrating the feasibility
of new analytical approaches prior to large-scale
replication~\cite{flyvbjerg2006five, yin2018case}.
Our use of it here is similarly motivated: we aim to establish
whether trajectory-based representations exhibit analyzable structure
at all, and to develop the methodological apparatus for future
comparative work across users and platforms.

The corpus comprises 1,122 sessions and 35,756 role-marked turns, spanning three
years (2023--2026).
We construct two parallel representations of the same underlying
data: a \emph{cognitive trajectory graph} that preserves sequential
dependencies between intermediate reasoning states, and QA-derived
representations constructed at two scales (a sampled subset
$n = 3{,}000$ and the full corpus $n = 15{,}384$) to rule out
sampling as a confound.

We analyze structural properties at two levels.
First, we characterize graph-level properties (refinement chain
length, relation type distribution, and long-chain
prevalence), comparing against SQuAD~\cite{rajpurkar2016squad} as
an external QA baseline.
Second, we use $\Delta\cos$ (an embedding-based metric capturing
how semantic similarity changes across consecutive steps) to measure
second-order transition dynamics across five controlled conditions:
random QA concatenation, semantic A$\to$Q stitching, a fully random
baseline, an order-shuffled counterfactual, topic-drift
stratification.

% ---------------------------------------------------------------
\subsection*{Key Findings}
% ---------------------------------------------------------------

Across all conditions, we observe consistent and statistically significant
differences between trajectory-based and QA-based representations.

\medskip
\noindent\textbf{Structural collapse.}\quad
Cognitive trajectory graphs exhibit a mean refinement chain length of
2.15 (max:~13; 8.6\% of chains $\geq$4~steps).
QA representations (whether sampled $n{=}3{,}000$ or exhaustive
$n{=}15{,}384$) collapse to chain length $\approx$1.1, with zero
long chains.
This pattern holds across sampling scales, ruling out sampling as an
explanation.

\medskip
\noindent\textbf{Non-recoverability.}\quad
Transition distributions differ significantly between real trajectories
and QA-derived sequences ($\text{KS}\;D = 0.298$).
Neither random QA concatenation nor semantic A$\to$Q matching recovers the original structure.  QA random concatenation yields substantially higher divergence 
($D = 0.298$) than semantic A$\to$Q matching ($D = 0.087$), 
but even the latter remains significantly different from real 
trajectories, indicating that local semantic continuity is 
insufficient to reconstruct higher-order dependencies.

\medskip
\noindent\textbf{Order dependence.}\quad
Shuffling the temporal order of real trajectory nodes (while preserving
content) produces comparable distributional shifts
($\text{KS}\;D = 0.101$), confirming that observed structure depends on
ordering rather than content alone.

\medskip
\noindent\textbf{Robustness.}\quad
These differences persist in low- and medium-drift strata
($\text{KS}\;D = 0.755 / 0.381$, both $p < 0.001$); the high-drift
stratum is inconclusive because it contains only 19 real transitions
($D = 0.180$, $p = 0.614$). Three distributional metrics converge:
KS distance, Wasserstein distance ($= 0.188$), and KL divergence
($= 1.074$).

% ---------------------------------------------------------------
\subsection*{Contributions}
% ---------------------------------------------------------------

This paper makes four contributions.

\begin{enumerate}

\item \textbf{A longitudinal case study methodology for analyzing
personal AI training data structure.}
We demonstrate that a single three-year personal interaction corpus
contains analyzable structural properties (refinement chain length,
transition dynamics, temporal ordering effects) that are inaccessible
to cross-sectional or aggregate approaches.
We provide a replicable pipeline enabling researchers to conduct
analogous analyses on their own corpora locally, without sharing raw
conversation content.

\item \textbf{Cognitive trajectory graphs as a generalizable
representational framework.}
We introduce a graph schema and construction algorithm applicable to
any longitudinal interaction corpus, independent of the specific user
or platform, and characterize its structural properties against
QA-derived representations at multiple scales.

\item \textbf{Empirical demonstration that QA slicing collapses
higher-order sequential dependencies.}
Through six controlled conditions and counterfactual constructions
on a single three-year corpus (including an order-shuffled
counterfactual that isolates temporal ordering as a structural
factor independent of content), we show that this collapse is a
structural consequence of the QA format rather than a sampling
artifact.
These findings motivate multi-user replication as the primary
direction for future work.

\item \textbf{``Dataset design is ontology design'' as a theoretical
framing for personal AI data practice.}
We argue that representational choices in training data construction
encode implicit assumptions about the nature of cognition, and that
in personal AI settings---where data volume is limited and individual
patterns are amplified---these choices deserve the same scrutiny as
model architecture decisions.
We introduce the \emph{consensus agent} as a distinct artifact from
a personal cognitive mirror, with different data architecture
requirements and evaluation criteria.

\end{enumerate}

Our findings are scoped to structural properties of data
representations derived from a single-user longitudinal corpus. Whether
these differences produce downstream behavioral gains requires a
separate, matched model evaluation and is outside this paper's scope.

% ================================================================
% SECTION 2: RELATED WORK
% ================================================================

\section{Related Work}
\label{sec:related}

Our work spans four areas of the research stack: model adaptation
for personalization, memory architectures for agent continuity,
longitudinal human--AI interaction, and training data representation.
We review each, focusing on what each layer assumes about interaction
data and what it leaves unexamined.

% ---------------------------------------------------------------
\subsection{Personalized Language Models}
\label{sec:related:personalization}
% ---------------------------------------------------------------

Personalization of dialogue systems has a long history in HCI and NLP.
Early work introduced persona-consistent dialogue, demonstrating that
models conditioned on explicit user profiles produce stylistically
coherent responses~\cite{zhang2018persona}.
Subsequent work scaled this approach to larger models and richer user
representations~\cite{thoppilan2022lamda}.

More recently, the challenge has shifted to \emph{continual}
personalization: adapting to users whose preferences evolve over time.
SPRInG~\cite{kim2026spring} addresses this by maintaining user-specific
LoRA adapters~\cite{hu2021lora} and selectively updating them on
high-novelty interactions, enabling adaptation to preference drift
without catastrophic forgetting.
Prefix-tuning~\cite{li2021prefix} and related parameter-efficient
methods provide the technical substrate for per-user adaptation.

While these approaches differ in mechanism, they often rely on
interaction data representations derived from query--response pairs
or sequential dialogue logs, implicitly treating each exchange as
conditionally independent given the current query (i.e., each response
is a function of the immediately preceding input, without modeling
accumulated reasoning history).
The question of whether this representational assumption is suitable
for capturing personal cognitive processes has not been examined.

% ---------------------------------------------------------------
\subsection{Memory Architectures for AI Agents}
\label{sec:related:memory}
% ---------------------------------------------------------------

A parallel line of work addresses personalization through memory
rather than fine-tuning.
Generative Agents~\cite{park2023generative} demonstrated that
agents equipped with structured memory---experience storage,
reflection, and planning---exhibit coherent long-term behavior,
establishing that memory organization is central to sustained
behavioral coherence.
Other approaches manage memory through OS-inspired paging between
an in-context working set and external storage~\cite{memgpt}.

These approaches primarily provide \emph{informational}
continuity, exposing past interactions at inference time without
altering the model's underlying inductive biases.
Recent work has noted that many graph-based memory architectures
rely on entity--relation triples or coarse text chunks as basic
units, which may fragment or coarsen the original
discourse~\cite{graphrag, zhou2025simple}. This observation highlights that the choice of
representation unit itself has structural consequences.

Our work isolates this issue at the training data level: we
evaluate whether QA slicing, the most widely used practice,
preserves the explicit representation of transition structure in 
longitudinal interaction data, or removes it from the training signal.

% ---------------------------------------------------------------
\subsection{Longitudinal Human--AI Interaction}
\label{sec:related:longitudinal}
% ---------------------------------------------------------------

HCI research has increasingly recognized that single-session studies
cannot capture how human--AI relationships evolve over time.
Karapanos et al.~\cite{karapanos2012longitudinal} identified
the need for longitudinal methods in HCI research, noting that
single-session evaluations miss temporal dynamics of technology
adoption and appropriation.
More recent work has highlighted that sustained use of AI systems
may reveal evolving patterns (including shifts in mental models,
task delegation, and perceived capabilities) that single-session
studies cannot capture~\cite{long2025longitudinal}.

Research on the cognitive effects of AI use has begun to characterize
how extended interaction reshapes human thought.
Kittur et al.~\cite{kittur2025tools} document how generative AI
alters knowledge work through iterative refinement loops,
meta-decision support, and schema induction. They characterize cognition
as a dynamic, multi-step process unfolding through iterative state
transitions.
Related work has examined cognitive load and engagement effects of
sustained AI assistance~\cite{kosmyna2025brain}.

These studies examine how AI affects human cognition.
Our work takes the inverse perspective: how the structural
representation of human cognitive processes in interaction logs affects
the training of personalized AI.

% ---------------------------------------------------------------
\subsection{Training Data Representation}
\label{sec:related:data}
% ---------------------------------------------------------------

The dominant paradigm for fine-tuning language models on dialogue
data is instruction tuning on query--response
pairs~\cite{ouyang2022rlhf}.
Chain-of-thought prompting~\cite{wei2022chain} demonstrated that
preserving intermediate reasoning steps---rather than only final
answers---improves performance on complex tasks, establishing that the
structure of reasoning, not just its conclusions, carries
informational value.
Our findings complement this line of work by demonstrating that
preserving intermediate reasoning steps is necessary but not
sufficient: if the temporal ordering of those steps is destroyed,
higher-order trajectory structure collapses regardless of whether
individual steps are retained.
Despite this, the implications for training data design in personal
AI settings have not been examined.
Prior work has largely treated data representation as an
implementation choice, with limited attention to how segmentation
decisions affect the preservation of cognitive structure across turns.

% ---------------------------------------------------------------
\subsection*{The Gap This Work Addresses}
% ---------------------------------------------------------------

Prior work across HCI and conversational AI has established that
single-session evaluations fail to capture the temporal dynamics of
human--AI interaction~\cite{karapanos2012longitudinal}, leading to a
shift toward longitudinal studies and large-scale interaction data.
However, this line of work has primarily focused on behavioral and
system-level phenomena, without formalizing the structural dependencies
within interaction trajectories themselves.

At the same time, dominant practices in training data construction
implicitly assume that interaction can be factorized into independent
query--response pairs, treating each step as locally conditioned on
the immediately preceding input.

What remains unexamined is whether this representational assumption
preserves the higher-order dependencies that may emerge in longitudinal
interaction.
If such dependencies exist, QA-based segmentation may systematically
distort the transition structure of interaction data.

This gap motivates our investigation.
We provide the first empirical characterization of whether QA-based
representations preserve or distort the transition dynamics of
longitudinal personal interaction data.

% ================================================================
% SECTION 3: METHOD
% ================================================================

\section{Method}
\label{sec:method}

We construct two parallel representations of the same longitudinal
interaction corpus and compare their structural properties.
Section~\ref{sec:chunking} describes the cognitive chunking procedure;
Section~\ref{sec:graph} defines the resulting graph representation.

% ---------------------------------------------------------------
\subsection{Cognitive Chunking}
\label{sec:chunking}
% ---------------------------------------------------------------

Raw conversation logs consist of interleaved user and assistant turns.
We process them into a cognitive graph $G = (V, E)$ through the
three-stage pipeline described in
Algorithms~\ref{alg:cognitive-chunking}--\ref{alg:detect-relation}.

\medskip
\noindent\textbf{Design principles.}\quad
The chunking algorithm is rule-based rather than learned, a deliberate 
design choice motivated by four constraints.

\emph{Reproducibility.} Rule-based segmentation produces identical 
outputs across runs given the same input, enabling exact replication 
without model checkpoints or stochastic sampling.

\emph{Determinism.} Fixed lexical rules avoid the variability introduced 
by LLM-based segmentation, where prompt sensitivity and version drift 
can alter chunk boundaries unpredictably.

\emph{Interpretability.} Each segmentation decision is traceable to 
an explicit rule (e.g., keyword overlap $< 30\%$ triggers topic shift), 
facilitating error analysis and allowing researchers to understand why 
a specific boundary was placed.

\emph{Ease of replication.} The algorithm requires no fine-tuned models, 
no API keys, and no proprietary services. Any researcher with the code 
can apply it to their own corpus locally, addressing the privacy 
constraints inherent to personal AI data.

The tradeoff is that rule-based detection may miss cognitive events 
without explicit linguistic markers. We address this limitation in 
Section~\ref{sec:limitations}; importantly, our structural findings 
(Section~\ref{sec:experiments}) are measured on the resulting graphs 
and are therefore independent of whether future work adopts different 
segmentation strategies.

\begin{algorithm}[tbp]
\caption{Cognitive Node Chunking and Graph Construction}
\label{alg:cognitive-chunking}
\begin{algorithmic}[1]
\Require Conversation turns $\mathcal{T} = \{t_1, \ldots, t_n\}$,
         where $t_i = (\text{role}_i, \text{content}_i)$
\Ensure Cognitive graph $G = (V, E)$

\State $V \gets \emptyset$,\; $E \gets \emptyset$

\For{each turn $t_i \in \mathcal{T}$}
    \State $S_i \gets$ split $t_i.\text{content}$ into sentences
    \State $V_i \gets$ \Call{MergeSentences}{$S_i$,\; $t_i.\text{role}$}
    \State $V \gets V \cup V_i$
\EndFor

\State $V \gets$ merge consecutive nodes with same role
       \hfill\Comment{Prevent consecutive same-role edges}

\For{each consecutive pair $(v_i,\, v_{i+1}) \in V$}
    \State $r \gets$ \Call{DetectRelation}{$v_i$,\; $v_{i+1}$}
    \State $E \gets E \cup \{(v_i,\, v_{i+1},\, r)\}$
\EndFor

\State $\mathcal{C} \gets$ find chains where edge type
       $\in \{\texttt{refines},\, \texttt{contrasts}\}$
\For{each chain $c = [v_\text{root}, \ldots, v_\text{final}] \in \mathcal{C}$
     with $|c| \geq 3$}
    \State $E \gets E \cup
           \{(v_\text{root},\, v_\text{final},\, \texttt{iteration\_final})\}$
\EndFor

\State \Return $G = (V, E)$
\end{algorithmic}
\end{algorithm}

\begin{algorithm}[tbp]
\caption{Sentence Merging with Cognitive Event Detection}
\label{alg:merge-sentences}
\begin{algorithmic}[1]
\Require Sentences $S = \{s_1, \ldots, s_m\}$, role $r$,
         minimum node length $\theta_\text{min} = 30$ chars
\Ensure Node set $V$

\State $V \gets \emptyset$,\; $v_\text{curr} \gets s_1$

\For{$i = 2$ \textbf{to} $m$}
    \State $\text{event} \gets \texttt{false}$
    \If{\Call{TopicShift}{$s_i,\, v_\text{curr}$}}
        $\text{event} \gets \texttt{true}$
        \hfill\Comment{Keyword overlap $< 30\%$}
    \ElsIf{\Call{ReasoningStep}{$s_i$}}
        $\text{event} \gets \texttt{true}$
        \hfill\Comment{\emph{so}, \emph{therefore}, \emph{thus}}
    \ElsIf{\Call{Correction}{$s_i$}}
        $\text{event} \gets \texttt{true}$
        \hfill\Comment{\emph{but}, \emph{however}, \emph{actually}}
    \ElsIf{\Call{NewIdea}{$s_i$}}
        $\text{event} \gets \texttt{true}$
        \hfill\Comment{\emph{what if}, \emph{maybe}}
    \ElsIf{\Call{PerspectiveShift}{$s_i$}}
        $\text{event} \gets \texttt{true}$
        \hfill\Comment{\emph{from another angle}}
    \EndIf

    \If{$\text{event} = \texttt{true}$ \textbf{and}
        $|v_\text{curr}| \geq \theta_\text{min}$}
        \State $V \gets V \cup \{(v_\text{curr},\, r)\}$
        \State $v_\text{curr} \gets s_i$
    \Else
        \State $v_\text{curr} \gets v_\text{curr} \oplus s_i$
               \hfill\Comment{Concatenate}
    \EndIf
\EndFor

\State $V \gets V \cup \{(v_\text{curr},\, r)\}$
\State \Return $V$
\end{algorithmic}
\end{algorithm}

\begin{algorithm}[tbp]
\caption{Relation Type Detection (priority order)}
\label{alg:detect-relation}
\begin{algorithmic}[1]
\Require Nodes $v_i$, $v_{i+1}$
\Ensure Relation type $r$

\If{\Call{Correction}{$v_{i+1}.\text{content}$}}
    \State \Return \texttt{refines}
    \hfill\Comment{Corrects or improves previous thought}
\ElsIf{\Call{PerspectiveShift}{$v_{i+1}.\text{content}$}}
    \State \Return \texttt{contrasts}
    \hfill\Comment{Alternative viewpoint}
\ElsIf{\Call{ReasoningStep}{$v_{i+1}.\text{content}$}}
    \State \Return \texttt{derives}
    \hfill\Comment{Logical inference from prior state}
\ElsIf{$v_i.\text{role} \neq v_{i+1}.\text{role}$}
    \State \Return \texttt{responds}
    \hfill\Comment{Role transition}
\Else
    \State \Return \texttt{follows}
    \hfill\Comment{Default sequential continuation}
\EndIf
\end{algorithmic}
\end{algorithm}

\medskip
\noindent\textbf{Design rationale.}\quad
Three design choices deserve explicit motivation.

\emph{Same-role merging} (Algorithm~\ref{alg:cognitive-chunking},
line~6) prevents the graph from encoding unnatural
assistant$\to$assistant sequences as reasoning edges, and avoids
identity collapse during fine-tuning.

\emph{Priority-ordered relation detection}
(Algorithm~\ref{alg:detect-relation}) ensures that the most
semantically meaningful relation type takes precedence when multiple
cognitive events co-occur in a single transition.

\emph{Iteration-final edges} capture the mapping from an initial
reasoning state to its converged conclusion, enabling training on
the complete arc of a correction chain rather than only its
intermediate steps.
Only chains of length $\geq 3$ (i.e., depth $\geq 2$) generate
\texttt{iteration\_final} edges, filtering trivial two-step revisions.

\medskip
\noindent\textbf{Limitation of current implementation.}\quad
Cognitive event detection is lexical and rule-based, relying on
surface markers to identify transition boundaries.
Transitions that occur without explicit linguistic signals---a user
implicitly reframing a problem without using contrastive
vocabulary---will not trigger a node boundary.
Incorporating embedding-based semantic distance ($\Delta\cos$) as a
segmentation criterion is a natural extension; we leave this for
future work.
Importantly, the main findings reported in Section~\ref{sec:experiments}
are measured on the resulting graph structure and transition
distributions, not derived from the segmentation rules, and are
therefore independent of this limitation.

% ---------------------------------------------------------------
\subsection{Graph Representation}
\label{sec:graph}
% ---------------------------------------------------------------

Each conversation is represented as a directed graph $G = (V, E)$.

\medskip
\noindent\textbf{Nodes.}\quad
Each node $v \in V$ encodes a cognitive state:
\[
v = \{\text{content}, \text{role}, \text{timestamp}, \text{length}\}.
\]
Timestamps are preserved from the original conversation records
(no missing timestamps observed across all 13,312 nodes in the corpus).

%\medskip
\noindent\textbf{Edges.}\quad
Each directed edge $e \in E$ carries a relation type from the vocabulary: 
\[
\{\texttt{follows},\, \texttt{derives},\, \texttt{refines},\, 
\texttt{contrasts},\, \texttt{responds},\, \texttt{iteration\_final}\}.
\]
\texttt{iteration\_final} edges are 
additive: they provide a direct shortcut from chain start to chain end 
without replacing the intermediate edges, enabling training on both 
step-by-step refinement and its converged outcome.

\medskip
\noindent\textbf{Extensibility.}\quad
The graph schema includes a \texttt{tags} field reserved for additional
relation types (e.g., analogy, hypothesis, example) that may emerge
from future unsupervised discovery over larger datasets.


% ================================================================
% SECTION 4: EXPERIMENTS
% ================================================================

\section{Experiments}
\label{sec:experiments}

We evaluate the cognitive trajectory graph representation against
QA-derived representations through structural analysis of the data
itself (graph properties
in Section~\ref{sec:structural}, trajectory dynamics via $\Delta\cos$
in Section~\ref{sec:dynamics}, and control experiments
in Section~\ref{sec:controls}).

Figure~\ref{fig:pipeline} summarizes the experimental pipeline.

\begin{figure}[t]
\centering
\small
\begin{tikzpicture}[
  node distance=0.8cm,
  box/.style={rectangle, draw, align=center, minimum width=3.5cm, minimum height=0.6cm},
  arrow/.style={->, >=stealth, thick}
]

% Top: Data processing
\node[box] (corpus) {Personal Interaction Corpus\\{\footnotesize 1,122 sessions, 35,756 turns}};
\node[box, below=of corpus] (chunking) {Cognitive Chunking\\{\footnotesize Algorithm 1--3}};
\node[box, below left=0.4cm and 0.8cm of chunking] (traj) {Trajectory Graphs\\{\footnotesize 1,122 graphs}};
\node[box, below right=0.4cm and 0.8cm of chunking] (qa) {QA Pairs\\{\footnotesize 3k sampled, 15k full}};

% Bottom: Experiments
\node[box, below=1.2cm of traj, fill=gray!10] (expA) {Exp. A: Structural\\{\footnotesize Table~\ref{tab:structural}}};
\node[box, right=0.3cm of expA, fill=gray!10] (expB) {Exp. B: $\Delta\cos$\\{\footnotesize Table~\ref{tab:deltacos}}};
\node[box, right=0.3cm of expB, fill=gray!10] (expC) {Exp. C: Controls\\{\footnotesize §\ref{sec:controls}}};

% Arrows
\draw[arrow] (corpus) -- (chunking);
\draw[arrow] (chunking) -- (traj);
\draw[arrow] (chunking) -- (qa);
\draw[arrow] (traj.south) |- (expA.north);
\draw[arrow] (traj.south) |- (expB.north);
\draw[arrow] (qa.south) |- (expA.north);
\draw[arrow] (qa.south) |- (expB.north);
\draw[arrow] (traj.south) |- (expC.north);
\draw[arrow] (qa.south) |- (expC.north);

\end{tikzpicture}
\caption{Experimental pipeline. A single corpus is processed into two 
parallel representations (trajectory graphs and QA pairs), which are 
compared across three experiment families: structural properties (A),
transition dynamics (B), and robustness controls (C).}
\label{fig:pipeline}
\end{figure}

\medskip
\noindent\textbf{Dataset.}\quad
The corpus consists of 1,122 personal conversation sessions (35,756
role-marked turns; average 31.9 turns per session, 632 characters per turn)
collected over three years (2023--2026).
Three representations are constructed from this corpus:
\textbf{Personal Cognitive} (1,122 trajectory graphs, one per deduplicated session),
\textbf{Personal QA Sampled} (3,000 QA graphs),
and \textbf{Personal QA Full} (15,384 QA graphs, covering the entire
corpus).
We additionally use \textbf{SQuAD}~\cite{rajpurkar2016squad}
(3,000 QA graphs) as an external baseline.
Embeddings are computed using \texttt{bge-m3}~\cite{chen2024bge}.
Session count and graph count are equal (1,122) because each session yields exactly one trajectory graph. Sentence-level segmentation is applied within each turn, but consecutive segments sharing the same role are subsequently merged. A node therefore approximates one conversational turn---or a run of same-role turns---rather than a sub-turn cognitive unit. The ratio of 13,312 nodes to 35,756 role-marked turns ($\approx 0.37$) reflects this merging.
% ---------------------------------------------------------------
\subsection{Structural Analysis}
\label{sec:structural}
% ---------------------------------------------------------------

We compare graph-level structural properties across all four
representations (Table~\ref{tab:structural}).

\begin{table}[h]
\centering
\caption{Structural comparison across dataset representations.
Personal QA results are stable across sampled and full-corpus
conditions, ruling out sampling as a confound.}
\label{tab:structural}
\small
\begin{tabular}{lcccc}
\toprule
\textbf{Metric}
  & \textbf{Cognitive}
  & \textbf{QA (3k)}
  & \textbf{QA (full)}
  & \textbf{SQuAD} \\
\midrule
Graphs
  & 1,122 & 3,000 & 15,384 & 3,000 \\
Avg chain length
  & \textbf{2.15} & 1.12 & 1.11 & 1.08 \\
Max chain length
  & \textbf{13} & 2 & 2 & 2 \\
Long chain ($\geq$4)
  & \textbf{8.6\%} & 0.0\% & 0.0\% & 0.0\% \\
derives + refines
  & 56.6\% & 67.0\% & 66.0\% & 36.2\% \\
Relation entropy
  & 1.735 & 1.582 & 1.609 & 1.218 \\
Avg input length
  & 365 & 363 & 380 & 127 \\
\bottomrule
\end{tabular}
\end{table}

\medskip
\noindent\textbf{Refinement chain collapse.}\quad
The cognitive representation exhibits substantially richer chain
structure: mean length 2.15, maximum 13, with 8.6\% of chains
containing four or more steps.
Both QA conditions---sampled and full-corpus---collapse to chain length
$\approx$1.1 with zero long chains and a maximum of two steps.
This result holds regardless of sampling scale, directly ruling out
sampling bias as an explanation.

\medskip
\noindent\textbf{The derives+refines paradox.}\quad
The QA representations show higher \textit{derives+refines} edge
proportions (66.0--67.0\%) than the cognitive representation (56.6\%).
This apparent reversal reflects a compression effect: QA segmentation
forces multi-turn reasoning into single nodes, concentrating
within-pair semantic relations.
Chain structure---which requires \emph{cross}-pair dependencies---is
eliminated entirely.
The two metrics together characterize what QA slicing loses: not
semantic density within pairs, but the connective structure across them.

% ---------------------------------------------------------------
\subsection{Trajectory Dynamics}
\label{sec:dynamics}
% ---------------------------------------------------------------

To compare transition dynamics, we compute $\Delta\cos$, a
second-order metric capturing how semantic similarity changes across
consecutive steps:

\begin{equation}
  \Delta\cos(t) =
    \cos(x_{t}, x_{t+1}) - \cos(x_{t-1}, x_{t})
  \label{eq:deltacos}
\end{equation}

where $\cos(\cdot,\cdot)$ denotes cosine similarity between
\texttt{bge-m3} embeddings~\cite{chen2024bge}.
$\Delta\cos$ captures trajectory \emph{curvature}: positive values
indicate increasing semantic coherence (continuation), negative values
indicate a direction shift.

We apply this metric to six sequence conditions
(Table~\ref{tab:deltacos}), comparing the $\Delta\cos$ distribution
of real cognitive trajectories (Group~A) against five alternatives
using two-sample KS tests.
We focus on KS statistic $D$ as the primary effect-size measure, as
$p$-values saturate under large sample sizes.

\begin{table}[t]
\centering
\caption{$\Delta\cos$ comparison across six sequence conditions.
KS~$D$ measures distributional distance from real trajectories (A).}
\label{tab:deltacos}
\small
\begin{tabular}{llcc}
\toprule
\textbf{Group} & \textbf{Condition} & \textbf{$n$} & \textbf{KS $D$ vs A} \\
\midrule
A & Real cognitive trajectories   & 11,417 & ---   \\
B & QA random concatenation       &  2,960 & 0.298 \\
C & QA semantic A$\to$Q stitching &  2,960 & 0.087 \\
D & Fully random baseline         &  4,404 & 0.168 \\
E & SQuAD external baseline       &  5,748 & 0.307 \\
F & Shuffled real (order removed) & 11,417 & 0.101 \\
\bottomrule
\end{tabular}
\end{table}

\medskip
\noindent\textbf{Structural divergence (A vs B).}\quad
Random QA concatenation differs substantially from real trajectories
($D = 0.298$, $p < 0.001$).
The ratio of $\Delta\cos$ variances between QA random concatenation 
and real trajectories ($3.82\times$) indicates that QA sequences exhibit
far greater distributional spread.
Notably, this elevated variance reflects not richer dynamics but 
structural discontinuity: the fully random baseline, by contrast, 
exhibits the narrowest distribution ($\sigma = 0.100$), as
independent random transitions produce near-zero second-order 
changes in high-dimensional embedding space. 
The high absolute cosine similarity observed in the fully random 
baseline ($\mu = 0.922$) reflects the narrow semantic range of 
short text chunks in this embedding space; all structural 
comparisons rely on the \emph{change} in similarity ($\Delta\cos$) 
rather than absolute values, controlling for this baseline effect.
Real trajectories occupy an intermediate position ($\sigma = 0.183$),
with structured semantic acceleration and deceleration producing 
moderate distributional spread.
Cohen's $d = 0.001$ reflects near-identical means across 
conditions---all $\Delta\cos$ distributions are centered near 
zero by construction---and should not be interpreted as indicating 
no effect.
The distributional difference captured by KS $D = 0.298$ is
a shape difference, not a mean difference: QA sequences and real 
trajectories differ in variance and modality, not in central 
tendency.

\medskip
\noindent\textbf{Semantic reconstruction fails (A vs C).}\quad
Even when QA pairs are stitched using answer-to-question semantic
matching---a method designed to preserve reasoning carryover---the
resulting sequences remain significantly different from real
trajectories ($D = 0.087$, $p < 0.001$).
Local semantic continuity is insufficient to reconstruct higher-order
trajectory structure, suggesting that the failure of QA representations 
is not a consequence of naive concatenation but a structural property 
of the QA format itself---one that persists even under semantically 
optimized reconstruction.

\medskip
\noindent\textbf{Order dependence (A vs F).}\quad
Shuffling the node order of real trajectories---preserving all content
but destroying temporal structure---produces a distributional shift
comparable to semantic reconstruction ($D = 0.101$, $p < 0.001$).
This experiment functions as a structural intervention on temporal
ordering: by permuting node sequence while preserving all segmentation
decisions and content, it isolates ordering as an independent
determinant of trajectory structure---one that cannot be attributed
to differences in vocabulary, topic, or semantic content between groups.
When identical content is randomly permuted, higher-order transition
dynamics collapse despite preserved semantic distributions, ruling out
content-level explanations entirely.


\medskip
\noindent\textbf{First-order continuity without second-order 
structure.}\quad
As a structural baseline, we compute first-order semantic 
similarity (cosine distance) within QA pairs across all three 
QA conditions. Personal QA (full corpus) exhibits an average 
semantic gap of 0.269 ($\text{similarity} = 0.731$); the
sampled condition yields 0.277 ($\text{similarity} = 0.723$),
confirming sampling stability (difference $< 3\%$).
Critically, second-order trajectory dynamics ($\Delta\cos$) 
are undefined for QA-derived sequences: all QA graphs consist 
of two-node structures, for which no consecutive triple 
$(x_{t-1}, x_t, x_{t+1})$ exists.
QA representations preserve local semantic continuity while lacking 
the multi-step sequential structure required to instantiate trajectory 
dynamics. This represents a structural absence rather than a performance 
deficit: the capacity to encode second-order dynamics cannot emerge from 
a two-node structure by construction. First-order continuity (high 
within-pair similarity) and second-order structure (trajectory curvature 
via $\Delta\cos$) are orthogonal properties; QA slicing preserves the 
former while making the latter undefined.

\medskip
\noindent\textbf{Distributional structure.}\quad
We examine the full $\Delta\cos$ distribution across transitions
rather than relying only on threshold-derived summaries. The six
conditions form a stable variance gradient: fully random sequences are
narrowest ($\sigma=0.100$), followed by shuffled real trajectories
($0.142$), real trajectories ($0.183$), semantic QA stitching
($0.205$), random QA concatenation ($0.358$), and SQuAD ($0.360$).
With a fixed reorientation threshold ($\Delta\cos < -0.1$), real
trajectories shift on 29.0\% of transitions, compared with 47.7\% for
random QA concatenation, 37.1\% for semantic stitching, 14.2\% for the
fully random baseline, and 20.4\% after shuffling real trajectories.
The higher QA rate reflects alternating within-pair proximity and
between-pair discontinuity, not richer trajectory structure.

\noindent\textbf{Native QA sequences.}\quad
This distributional analysis applies to QA pseudo-trajectories
constructed by concatenation.
Native QA-derived sequences---the direct output of QA
slicing---consist entirely of two-node graphs, for which no
consecutive triple $(x_{t-1}, x_t, x_{t+1})$ exists.
Second-order transition dynamics ($\Delta\cos$) are therefore
structurally undefined for native QA, not merely absent as
a performance outcome.

% ---------------------------------------------------------------
\subsection{Control Experiments}
\label{sec:controls}
% ---------------------------------------------------------------

We conduct three additional controls to verify that observed differences
are not artifacts of confounding factors.

\medskip
\noindent\textbf{Topic drift stratification.}\quad
We stratify transitions by baseline semantic similarity
($\cos(x_{t-1}, x_t)$) into three drift regimes---low ($> 0.7$),
medium ($0.3$--$0.7$), and high ($< 0.3$)---and apply KS tests within
each stratum.
Real trajectories and QA sequences differ significantly in the low-
and medium-drift regimes ($D = 0.755 / 0.381$; both $p < 0.001$).
The high-drift stratum is small (19 real transitions) and inconclusive
($D = 0.180$, $p = 0.614$). We therefore do not claim robustness under
extreme topic shifts; the supported result is that ordinary low- and
medium-drift differences are not explained by endpoint similarity.

\medskip
\noindent\textbf{Sampling invariance.}\quad
The structural analysis is replicated with the full QA corpus
(15,384 graphs) versus the sampled condition (3,000 graphs).
Average chain length is stable (1.11 vs 1.12) and long-chain
prevalence remains 0.0\% in both conditions, ruling out sampling as a
confound in the structural results.

\medskip
\noindent\textbf{Distributional robustness.}\quad
Beyond KS distance, we report two additional distributional metrics:
Wasserstein (Earth Mover) distance ($= 0.188$) and KL divergence
($= 1.074$).
All three metrics converge in direction and magnitude, providing
convergent evidence that the observed differences are not an artifact
of any single statistical measure.

% ---------------------------------------------------------------
% ================================================================
% SECTION 5: DISCUSSION
% ================================================================

\section{Discussion}
\label{sec:discussion}

Our findings demonstrate that QA slicing does not merely lose
information---it fundamentally alters the statistical structure of
cognitive trajectories by collapsing history-dependent state
transitions into locally conditioned responses.
We discuss five implications.

% ---------------------------------------------------------------
\subsection{Dataset Design Is Ontology Design}
\label{sec:discussion:ontology}
% ---------------------------------------------------------------

The choice of how to segment interaction data is not a neutral
preprocessing decision---it encodes an implicit assumption about
what thinking \emph{is}.

Our results operationalize this claim: the same underlying interaction corpus, segmented differently, yields representations with measurably different statistical properties.

For general-purpose AI trained at scale, structural assumptions in
training data may average out across billions of examples.
For personal AI trained on hundreds of conversations from a single
user, every representational decision is amplified.
The implication is not that QA segmentation is wrong in general, but
that its suitability for personal AI cannot be assumed---it must be
empirically evaluated.

This observation connects to a broader principle in data-centric AI:
the structure imposed on training data determines what patterns a
model can learn, independent of model architecture or optimization
procedure.
In personal AI settings, where the goal is to capture the cognitive
style of a specific individual, the ontological commitments embedded
in data formatting deserve the same scrutiny as model design choices.


% ---------------------------------------------------------------
\subsection{The ``Consensus Agent'' and Its Implications}
\label{sec:discussion:consensus}
% ---------------------------------------------------------------

The source corpus is dyadic: user turns redirect the conversation and
assistant turns develop, revise, or consolidate responses. The graphs
therefore describe structure that emerged through sustained
interaction; they do not isolate either participant's private
cognition. We use \emph{consensus agent} as a design concept for a
system intended to model this co-evolved collaborative history, rather
than as a claim about a model evaluated in this paper.

Trajectory representation may be relevant to such an artifact because
it retains revision paths that QA slicing removes. This is a statement
about the supervision available in the data, not evidence that a
fine-tuned model will use that supervision correctly. Establishing the
latter requires a separate, leakage-free behavioral comparison.

A consensus agent and a personal cognitive mirror are different
artifacts with different use cases.

\begin{table}[h]
\centering
\small
\caption{Consensus agent vs.\ personal cognitive mirror.}
\label{tab:agent-types}
\begin{tabular}{lll}
\toprule
\textbf{Artifact} & \textbf{Primary data} & \textbf{Target behavior} \\
\midrule
Consensus agent   & Dyadic trajectories & Collaborative history \\
Cognitive mirror  & User-side evidence  & Individual reasoning \\
\bottomrule
\end{tabular}
\end{table}

The former targets a long-term collaborative partner shaped by joint
dialogue history; the latter requires a data architecture and
evaluation protocol that treat user-side contributions as the primary
evidence. The present structural study establishes neither artifact;
it clarifies that they require different representational commitments.

% ---------------------------------------------------------------
\subsection{Memory Injection vs.\ Weight Internalization}
\label{sec:discussion:memory}
% ---------------------------------------------------------------

Our work is motivated by a distinction between two mechanisms of AI
personalization: injecting information into context at inference time,
and modifying model weights through fine-tuning.

Retrieval-augmented and memory-injection approaches~\cite{memgpt,
park2023generative} operate at the inference layer: the model is
\emph{told} about a user's history at each interaction.
Fine-tuning operates at the weight layer: the model's default behavior
is shaped by exposure to a user's interaction history.

We hypothesize that these mechanisms differ qualitatively, not just
quantitatively.
Context injection produces informational continuity: the model knows
what happened.
Weight modification may produce something closer to cognitive
continuity: the model's default reasoning tendencies are shifted.
Our results show that representation structure constrains what
sequential information is available to a learning system, prior to any
choice of storage mechanism.

The analogy is the difference between being \emph{informed} of past
experiences and having \emph{lived} through them.

\medskip
\noindent\textbf{Long context vs.\ trajectory structure.}\quad
An immediate question is whether long-context models obviate the need 
for structured representations. We argue they address different problems. 
Long context solves an \emph{access} problem: how to expose more 
interaction history within a single forward pass. Trajectory 
representation addresses a \emph{training signal} problem: whether 
the structure of multi-step reasoning is explicitly represented in 
the data a model is fine-tuned on. A long-context model fine-tuned 
on QA pairs still receives no explicit supervision for the sequential
dependencies that trajectory graphs encode. Trajectory data can expose
those dependencies, but whether a model learns to use them is an
empirical question. The mechanisms are therefore complementary rather
than substitutive.

\medskip
QA-formatted data exposes locally conditioned transitions. Trajectory
data preserves a higher-order signal that a downstream learning method
could exploit. The present study establishes the difference in that
available signal; it does not claim that preservation alone produces
cognitive continuity or better model behavior.

% ---------------------------------------------------------------
\subsection{Structural Difference as a Precondition}
\label{sec:discussion:precondition}
% ---------------------------------------------------------------

Our structural experiments establish that trajectory-based and
QA-based representations differ in what they retain. This difference
is a precondition for a downstream representation comparison, not its
outcome: preserving structure is necessary for learning from it but is
not sufficient to guarantee that a model will exploit it.

Standard example-level fine-tuning commonly shuffles samples and
optimizes a per-example objective. Such a procedure may ignore the
longer-range dependencies preserved in a trajectory graph. A stronger
behavioral test therefore requires leakage-free QA and trajectory
baselines matched on source sessions, model, budget, and temporal split,
plus an order-aware objective or batching strategy where appropriate.
We leave that behavioral question to separate work.

% ---------------------------------------------------------------
\subsection{Design Implications}
\label{sec:discussion:implications}
% ---------------------------------------------------------------

Our findings carry three implications for researchers and
practitioners building personal AI systems.

\medskip
\noindent\textbf{Representation format is a design decision,
not a default.}\quad
The choice to segment interaction data into QA pairs is rarely
made explicitly---it is inherited from general-purpose fine-tuning
practice.
Our results demonstrate that this default carries measurable
structural consequences: the same underlying corpus, segmented
differently, yields representations with significantly different
transition dynamics.
Researchers and designers building personal AI systems should treat
data format as a first-class design decision, evaluated against
explicit criteria for what cognitive structure the format is
intended to preserve.

\medskip
\noindent\textbf{Temporal ordering should be treated as a
feature, not metadata.}\quad
The order-shuffled counterfactual (Group~F, KS $D = 0.101$)
demonstrates that the structural properties of personal interaction
data depend on temporal ordering independently of content.
Interaction logs should preserve original conversation timestamps
and sequential context as primary structural signals---not merely
as provenance metadata---and pipeline designs should treat
order-scrambling as a measurable form of information loss.

\medskip
\noindent\textbf{Distinguish the artifact before choosing the
architecture.}\quad
The consensus agent and the personal cognitive mirror are
different artifacts requiring different data architectures and
evaluation criteria.
A system intended to approximate a long-term collaborative
partner would draw on dyadic trajectories structured as graphs.
A system intended to capture a user's individual reasoning style
would require user-side contributions as the primary training
signal---a design problem that remains open.
Making this distinction explicit at the outset of a personal AI
project determines which data collection strategy, segmentation
method, and evaluation framework is appropriate, and prevents
optimizing for the wrong artifact.

% ================================================================
% SECTION 6: LIMITATIONS
% ================================================================

\section{Limitations}
\label{sec:limitations}

We identify six limitations of the current work.

\medskip
\noindent\textbf{Single-user longitudinal design.}\quad
This study analyzes one user's interaction history over three years,
a design choice with explicit tradeoffs.
The depth it enables (tracking structural properties across thousands
of sessions, controlling for individual cognitive style across the
full corpus, and isolating temporal ordering effects within a single
user's reasoning patterns) is not achievable through multi-user
aggregate approaches at comparable data resolution.

Single-user longitudinal design is not a limitation to be apologized 
for, but a methodological choice suited to personal AI research. 
Personal AI systems are designed to capture individual cognitive 
patterns, not population averages. A three-year interaction history 
from one user provides deeper temporal structure than cross-sectional 
snapshots from thousands of users. 

We intentionally prioritize \emph{internal validity} over 
\emph{external validity}: the question this study addresses 
is whether trajectory structure exists at all in longitudinal 
interaction data and whether QA slicing removes it. Demonstrating 
the phenomenon's presence in a single corpus with high internal 
validity establishes feasibility and motivates multi-user 
replication as the natural next step. Attempting to claim 
cross-user generalizability from aggregate data would sacrifice 
the temporal depth required to observe structural properties in 
the first place. Direct generalizability claims across users are
outside the scope of this study.

Whether the structural properties reported here---refinement chain
length, transition dynamics, order dependence---are characteristic
of personal interaction data broadly, or reflect this user's specific
cognitive style, is an empirical question multi-user replication would
address.
We note that the methodological contributions of this work---the
cognitive chunking pipeline, the graph schema, and the controlled
comparison framework---are user-agnostic and designed for local
replication: researchers can apply the same pipeline to their own
interaction data without sharing raw conversation content, using the
code and synthetic example data we release alongside this paper.
We treat multi-user replication as the primary direction for future
work rather than a limitation of the present design.

\medskip
\noindent\textbf{Rule-based segmentation.}\quad
The cognitive chunking pipeline relies on lexical markers to detect
cognitive event boundaries, capturing surface signals of reasoning
transitions but potentially missing transitions without explicit
linguistic markers.
Incorporating embedding-based semantic distance as a segmentation
criterion is a natural extension we leave for future work.
Importantly, the main findings reported in
Section~\ref{sec:experiments}---order dependence and
non-recoverability---are measured on resulting graph structure and
transition distributions, not derived from the segmentation rules
themselves, and are therefore unlikely to be fully explained by this limitation.
The shuffled-trajectory experiment (Group F) provides partial evidence that the observed structure is not an artifact of the segmentation rules: shuffling node order while preserving all segmentation decisions produces a significant distributional shift (KS $D =0.101$, $p < 0.001$), indicating that structure depends on the temporal ordering of states, not on how those states were defined.

\medskip
\noindent\textbf{Cognitive nodes as text chunks.}\quad
Graph nodes approximate cognitive states through rule-based text
segmentation.
A true cognitive state would require richer modeling: capturing
epistemic status, confidence, and relation to prior beliefs, not
just textual content.
The gap between a text chunk and a cognitive state is a fundamental
challenge for any approach that operationalizes cognition from
interaction logs.

\medskip
\noindent\textbf{Consensus agent, not cognitive mirror.}\quad
The source conversations are co-produced by a user and an assistant.
Our graph representation captures textual transition structure in that
dyadic history; it cannot identify which patterns belong to the user's
individual cognition, the assistant's response policy, or their
interaction. A cognitive mirror would require user-centered evidence
and a different validation design.

\medskip
\noindent\textbf{Scope of findings.}\quad
Our findings characterize one personal corpus under one segmentation
method compared against one external QA baseline.
The claim is not that cognitive trajectory graphs are the correct
representation for personal AI training data, but that the choice of
representation is consequential and has been underexamined.
Alternative representations---hierarchical graphs, temporal knowledge
bases, episodic memory structures---may capture different aspects of
the same cognitive processes, and comparative evaluation across
representation types is a productive direction for future work.

\medskip
\noindent\textbf{Curvature metric.}\quad
Finally, we explored trajectory curvature as a second-order 
metric capturing the directional consistency of semantic 
transitions, but found that high-dimensional embedding spaces 
produce near-universal negative curvature values, making 
interpretation difficult. Developing curvature metrics robust 
to dimensionality effects is a direction for future work.

\bibliographystyle{ACM-Reference-Format}
\bibliography{refs}

\end{document}
