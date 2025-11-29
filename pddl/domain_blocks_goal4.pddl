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
  )

  ;; Pick up a block from the table (NOT at a goal position)
  (:action pickup
    :parameters (?x - block)
    :precondition (and
      (ontable ?x)
      (clear ?x)
      (handempty)
    )
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; Pick up a block from a specific position
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
    )
  )

  ;; Put down a block at a specific position
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
    )
  )

  ;; Unstack from a block (NOT at a goal position)
  (:action unstack
    :parameters (?x - block ?y - block)
    :precondition (and
      (on ?x ?y)
      (clear ?x)
      (handempty)
    )
    :effect (and
      (holding ?x)
      (clear ?y)
      (not (on ?x ?y))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; Unstack from a block at a specific position
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

  ;; Stack on top of another block at a specific position
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
    )
  )
)
