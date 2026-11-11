fun transform(xs : list<int>) : list<int>
  match xs
    Cons(x,xx) -> Cons(x+1, transform(xx))
    Nil -> Nil

fun main()
  println(transform(list(1,1000)).sum)
  val xs = list(1,1000)
  println(transform(xs).sum)
  println(xs.sum)
