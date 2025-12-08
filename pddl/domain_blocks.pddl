(define (domain blocks)
  (:requirements :strips :typing)
  (:types block)

  (:predicates
    (ontable ?x - block)
    (on ?x - block ?y - block)
    (clear ?x - block)
    (holding ?x - block)
    (handempty)
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

  ;; put down a block on the table
  (:action putdown
    :parameters (?x - block)
    :precondition (holding ?x)
    :effect (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (not (holding ?x))
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

  ;; place a held block on top of another block
  (:action stack
    :parameters (?x - block ?y - block)
    :precondition (and
      (holding ?x)
      (clear ?y)
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
