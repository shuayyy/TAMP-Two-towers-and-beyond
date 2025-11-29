(define (domain blocks-goal4)
  (:requirements :strips :typing)
  (:types block position)

  (:predicates
    ;; Standard blocksworld predicates
    (ontable ?x - block)
    (on ?x - block ?y - block)
    (clear ?x - block)
    (holding ?x - block)
    (handempty)

    ;; Positional predicates for Goal 4
    (at-position ?x - block ?p - position)
    (position-free ?p - position)

    ;; Helper: true if block is scattered (not at any goal position)
    (scattered ?x - block)
  )

  ;; Pick up a scattered block (not at a goal position)
  (:action pickup
    :parameters (?x - block)
    :precondition (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (scattered ?x)
    )
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; Pick up a block from a specific goal position
  (:action pickup-at
    :parameters (?x - block ?p - position)
    :precondition (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (at-position ?x ?p)
    )
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
      (not (at-position ?x ?p))
      (position-free ?p)
      (scattered ?x)  ;; Block is now scattered again
    )
  )

  ;; Put down a block anywhere (becomes scattered)
  (:action putdown
    :parameters (?x - block)
    :precondition (holding ?x)
    :effect (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (not (holding ?x))
      (scattered ?x)
    )
  )

  ;; Put down a block at a specific goal position
  (:action putdown-at
    :parameters (?x - block ?p - position)
    :precondition (and
      (holding ?x)
      (position-free ?p)
    )
    :effect (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (not (holding ?x))
      (at-position ?x ?p)
      (not (position-free ?p))
      (not (scattered ?x))  ;; Block is no longer scattered
    )
  )

  ;; Unstack from a scattered block
  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and
      (on ?x ?y)
      (clear ?x)
      (handempty)
      (scattered ?y)
    )
    :effect (and
      (holding ?x)
      (clear ?y)
      (not (on ?x ?y))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; Unstack from a block at a specific goal position
  (:action unstack-at
    :parameters (?x - block ?y - block ?p - position)
    :precondition (and
      (on ?x ?y)
      (clear ?x)
      (handempty)
      (at-position ?y ?p)
    )
    :effect (and
      (holding ?x)
      (clear ?y)
      (not (on ?x ?y))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; Stack on a scattered block
  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and
      (holding ?x)
      (clear ?y)
      (scattered ?y)
    )
    :effect (and
      (on ?x ?y)
      (clear ?x)
      (not (clear ?y))
      (handempty)
      (not (holding ?x))
      (scattered ?x)  ;; Stacked block is also scattered
    )
  )

  ;; Stack on top of a block at a specific goal position
  (:action stack-at
    :parameters (?x - block ?y - block ?p - position)
    :precondition (and
      (holding ?x)
      (clear ?y)
      (at-position ?y ?p)
    )
    :effect (and
      (on ?x ?y)
      (clear ?x)
      (not (clear ?y))
      (handempty)
      (not (holding ?x))
      ;; NOTE: x is NOT at position ?p - it's stacked on top
      ;; If goal requires x at a position, that position should be specified separately
    )
  )
)
