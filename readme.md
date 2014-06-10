# MySignature - Sublime Text Package

Wide JavaScript autocomplete functionality for [Sublime Text][] with `method/function` signature (arguments) and `var` completion. (You can usually make the completion box show up with Ctrl+Space in a js file.)

The package will keep an index of methods/functions seen in .js files doing a dumb parsing: it looks for `name = function(...)` and `name: function(...)`. It does not evaluate objects.

Since version 2, files are parsed only the first time these are seen and then will only reparse a file if you save it (to keep the index up to date.)

As source for its index will look into:

-   All the js files of the current opened projects/folders. (this includes all the windows and scans for changes periodically in an optimized way, a file is only parsed in case of a cache miss)

-   If you open a js file that is outside the current project, it will scan the folder where this file resides.

-   Completion of methods/functions in unsaved files, and completion of `var`s for the current file are generated on the fly, with the incredible fast API of Sublime Text.

Will trigger its magic in js files and js scopes (eg in a script tag of an HTML file.)

For the original development read about at <http://www.eladyarkoni.com/2012/09/sublime-text-auto-complete-plugin.html>

For the performance improvements take a look to https://github.com/eladyarkoni/MySignaturePlugin/pull/7

Enjoy!

2012 Elad Yarkoni

2014 Tito Bouzout \<tito.bouzout@gmail.com\>

  [Sublime Text]: http://www.sublimetext.com/3
