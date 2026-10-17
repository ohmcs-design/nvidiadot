package dot.java;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * DOT AI Java Code Intelligence Engine
 * Parses Java files in the workspace, extracting packages, classes, methods, and imports.
 * Emits JSON-formatted AST overview for the NVIDIA AI Workforce.
 */
public class CodeAnalyzer {

    static class JavaFileInfo {
        String filename;
        String packageName = "";
        List<String> imports = new ArrayList<>();
        List<String> classes = new ArrayList<>();
        List<String> methods = new ArrayList<>();
    }

    private static final Pattern PACKAGE_PATTERN = Pattern.compile("^\\s*package\\s+([a-zA-Z0-9_.]+);", Pattern.MULTILINE);
    private static final Pattern IMPORT_PATTERN = Pattern.compile("^\\s*import\\s+([a-zA-Z0-9_.*]+);", Pattern.MULTILINE);
    private static final Pattern CLASS_PATTERN = Pattern.compile("(public|protected|private)?\\s*(class|interface|enum)\\s+([a-zA-Z0-9_]+)", Pattern.MULTILINE);
    private static final Pattern METHOD_PATTERN = Pattern.compile("(public|protected|private)?\\s+([a-zA-Z0-9_<>\\[\\]]+)\\s+([a-zA-Z0-9_]+)\\s*\\(([^)]*)\\)\\s*(throws\\s+[a-zA-Z0-9_,\\s]+)?\\s*\\{", Pattern.MULTILINE);

    public static JavaFileInfo analyzeFile(File file) {
        JavaFileInfo info = new JavaFileInfo();
        info.filename = file.getName();

        try {
            String content = Files.readString(file.toPath());

            Matcher pkgMatcher = PACKAGE_PATTERN.matcher(content);
            if (pkgMatcher.find()) {
                info.packageName = pkgMatcher.group(1);
            }

            Matcher impMatcher = IMPORT_PATTERN.matcher(content);
            while (impMatcher.find()) {
                info.imports.add(impMatcher.group(1));
            }

            Matcher classMatcher = CLASS_PATTERN.matcher(content);
            while (classMatcher.find()) {
                info.classes.add(classMatcher.group(2) + " " + classMatcher.group(3));
            }

            Matcher methodMatcher = METHOD_PATTERN.matcher(content);
            while (methodMatcher.find()) {
                String returnType = methodMatcher.group(2);
                String methodName = methodMatcher.group(3);
                String params = methodMatcher.group(4).trim();
                info.methods.add(returnType + " " + methodName + "(" + params + ")");
            }

        } catch (IOException e) {
            info.classes.add("[Error reading file: " + e.getMessage() + "]");
        }

        return info;
    }

    public static void scanDirectory(File dir, List<JavaFileInfo> results) {
        File[] files = dir.listFiles();
        if (files == null) return;

        for (File f : files) {
            if (f.isDirectory()) {
                if (!f.getName().equals(".git") && !f.getName().equals("target") && !f.getName().equals(".idea")) {
                    scanDirectory(f, results);
                }
            } else if (f.getName().endsWith(".java")) {
                results.add(analyzeFile(f));
            }
        }
    }

    public static void main(String[] args) {
        String targetPath = args.length > 0 ? args[0] : ".";
        File target = new File(targetPath);

        List<JavaFileInfo> results = new ArrayList<>();
        if (target.isDirectory()) {
            scanDirectory(target, results);
        } else if (target.getName().endsWith(".java")) {
            results.add(analyzeFile(target));
        }

        // Output JSON
        StringBuilder json = new StringBuilder();
        json.append("{\n  \"analyzed_files\": [\n");
        for (int i = 0; i < results.size(); i++) {
            JavaFileInfo info = results.get(i);
            json.append("    {\n");
            json.append("      \"file\": \"").append(info.filename).append("\",\n");
            json.append("      \"package\": \"").append(info.packageName).append("\",\n");
            json.append("      \"classes\": ").append(listToJson(info.classes)).append(",\n");
            json.append("      \"methods\": ").append(listToJson(info.methods)).append(",\n");
            json.append("      \"imports\": ").append(listToJson(info.imports)).append("\n");
            json.append("    }").append(i < results.size() - 1 ? "," : "").append("\n");
        }
        json.append("  ]\n}");

        System.out.println(json.toString());
    }

    private static String listToJson(List<String> list) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < list.size(); i++) {
            sb.append("\"").append(list.get(i).replace("\"", "\\\"")).append("\"");
            if (i < list.size() - 1) sb.append(", ");
        }
        sb.append("]");
        return sb.toString();
    }
}
