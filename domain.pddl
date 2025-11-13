;; PDDL Domain for Block Stacking (Person 1)
;; Task and Motion Planning Project - Goal 1: Building the Two Towers
;;
;; This domain defines the blocksworld problem for manipulating 6 colored blocks
;; to build two towers:
;;   Tower 1: RED-GREEN-BLUE (top to bottom)
;;   Tower 2: YELLOW-MAGENTA-CYAN (top to bottom)
;;
;; Based on classic STRIPS blocksworld domain
;; Author: Person 1

(define (domain blocksworld)
  (:requirements :strips)

  (:predicates
    (on ?x ?y)        ;; block ?x is on block ?y
    (ontable ?x)      ;; block ?x is on the table
    (clear ?x)        ;; nothing is on top of block ?x
    (holding ?x)      ;; robot gripper is holding block ?x
    (handempty)       ;; robot gripper is empty
  )

  ;; PICK-UP: Pick up a block from the table
  ;; Precondition: block is on table, block is clear, hand is empty
  ;; Effect: holding the block, block not on table, hand not empty
  (:action pick-up
    :parameters (?x)
    :precondition (and
      (clear ?x)
      (ontable ?x)
      (handempty)
    )
    :effect (and
      (holding ?x)
      (not (ontable ?x))
      (not (clear ?x))
      (not (handempty))
    )
  )

  ;; PUT-DOWN: Put down a block onto the table
  ;; Precondition: holding the block
  ;; Effect: block is on table, block is clear, hand is empty
  (:action put-down
    :parameters (?x)
    :precondition (holding ?x)
    :effect (and
      (ontable ?x)
      (clear ?x)
      (handempty)
      (not (holding ?x))
    )
  )

  ;; STACK: Stack a block on top of another block
  ;; Precondition: holding top block, bottom block is clear
  ;; Effect: top block is on bottom block, top block is clear, hand is empty,
  ;;         bottom block is not clear
  (:action stack
    :parameters (?top ?bottom)
    :precondition (and
      (holding ?top)
      (clear ?bottom)
    )
    :effect (and
      (on ?top ?bottom)
      (clear ?top)
      (handempty)
      (not (holding ?top))
      (not (clear ?bottom))
    )
  )

  ;; UNSTACK: Remove a block from on top of another block
  ;; Precondition: top block is on bottom block, top block is clear, hand is empty
  ;; Effect: holding top block, bottom block is clear, top block not on bottom,
  ;;         hand not empty
  (:action unstack
    :parameters (?top ?bottom)
    :precondition (and
      (on ?top ?bottom)
      (clear ?top)
      (handempty)
    )
    :effect (and
      (holding ?top)
      (clear ?bottom)
      (not (on ?top ?bottom))
      (not (clear ?top))
      (not (handempty))
    )
  )
)
