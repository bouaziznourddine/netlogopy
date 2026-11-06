package org.nlogo.headless;

import java.util.Arrays;
import java.util.ArrayList;

/** Answers shared by the fake headless workspace and the fake App. */
public class Fake {
    public static String lastLabel = "";

    public static void command(String source) {
        if (source.startsWith("bad")) {
            throw new RuntimeException("Nothing named BAD has been defined.");
        }
    }

    public static Object report(String source) {
        if (source.equals("list")) return new ArrayList<Object>(Arrays.asList(1.0, 2.5));
        if (source.equals("can")) return Boolean.FALSE;
        if (source.startsWith("set_label_turtle")) {
            lastLabel = source.substring(source.indexOf('"') + 1, source.lastIndexOf('"'));
            return Double.valueOf(0);
        }
        if (source.startsWith("get_label_turtle")) return lastLabel;
        if (source.startsWith("fdfd")) return Double.valueOf(0);
        throw new RuntimeException("Nothing named " + source.split(" ")[0].toUpperCase()
                                   + " has been defined.");
    }
}
