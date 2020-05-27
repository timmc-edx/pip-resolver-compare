Script for running both pip dependency resolvers.

See http://www.ei8fdb.org/thoughts/2020/05/test-pips-alpha-resolver-and-help-us-document-dependency-conflicts/

Run::

  for d in ~/repos/*; do ./install-with-both.py "$d"; done

Find mismatched resolution outcomes::

  for r in ~/tmp/test-pip-alpha-resolver/*; do
    diff "$r"/*-{main,alpha}/freeze_out.txt >/dev/null \
    || echo "Package list mismatch in $(grep ^d $r/*-main/info.txt | tail -c+4) ($r)"
  done | sort
