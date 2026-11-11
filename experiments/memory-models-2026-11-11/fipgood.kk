fip fun reverse-owned(xs : list<a>, acc : list<a>) : list<a>
  match xs
    Cons(x,xx) -> reverse-owned(xx, Cons(x,acc))
    Nil -> acc

fun main()
  println(reverse-owned([1,2,3], Nil).head)
