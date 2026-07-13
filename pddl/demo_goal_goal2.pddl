(define (problem demo_goal)
  (:domain blocks)
  (:objects
    r g b y m c - block
  )
  (:init
    (clear c)
    (clear m)
    (handempty)
    (on b r)
    (on m y)
    (on r g)
    (on y b)
    (ontable c)
    (ontable g)
  )
  (:goal
    (and
      (clear m)
      (handempty)
      (on b r)
      (on m y)
      (on r g)
      (on y b)
      (ontable g)
    )
  )
)
