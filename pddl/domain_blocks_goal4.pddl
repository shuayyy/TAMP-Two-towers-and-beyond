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
    ;; A block is at a specific (x, y, z) position
    (at-position ?x - block ?p - position)

    ;; Helper predicate to mark positions as occupied
    (position-free ?p - position)
  )

  ;; pick up a block from the table
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

  ;; put down a block on the table at a specific position
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

  ;; pick up the top block from a stack
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

  ;; place a held block on top of another block at a specific position
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
