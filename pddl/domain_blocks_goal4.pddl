(define (domain blocks-goal4)
  (:requirements :strips :typing)
  (:types block position)

  (:predicates
    (ontable ?x - block)
    (on ?x - block ?y - block)
    (clear ?x - block)
    (holding ?x - block)
    (handempty)
    (at-position ?x - block ?p - position)
    (position-free ?p - position)
  )

  ;; Simple pickup - ignores positions
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

  ;; Put down at specific position
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

  ;; Simple unstack
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

  ;; Stack on block at position
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
