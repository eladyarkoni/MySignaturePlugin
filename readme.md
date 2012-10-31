MySignature - Sublime text 2 plugin
-------------------------------------

MySignature plugin is very lightweight plugin for sublime which improve the sublime text autocomplete functionality.

Each method in the autocomplete pop-up box is presented with its signature (method name and arguments) using SublimeText's "auto_complete" box. (You can usually make this box show up with Ctrl+Space.)

This plugin works on save: when you save any file in your project, the plugin maps all your javascript methods of the form `var name = function() {}` and `name: function() {}`. When the complete box is opened (ctrl+space or by the editor), it shows the methods in your project files with the signature. (It currently does not support minified files since the method used is a line-by-line search.)

This plugin is for Javascript Developers only.

Please read more about the plugin and its development at http://www.eladyarkoni.com/2012/09/sublime-text-auto-complete-plugin.html. 

Enjoy!

Elad Yarkoni.   