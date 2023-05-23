<h1 align="center">
  <a href="https://github.com/ankitwasankar/mftool-java">
    <img src="https://raw.githubusercontent.com/ankitwasankar/mftool-java/master/src/main/resources/icons/mf-tool-java-new.jpg" alt="mftool-java">
  </a>
</h1>
<p align="center">
<a target="_blank" href="https://search.maven.org/artifact/com.webencyclop.core/mftool-java"><img src="https://img.shields.io/maven-central/v/com.webencyclop.core/mftool-java.svg?label=Maven%20Central"/></a> 
<a target="_blank" href="https://www.codacy.com/gh/ankitwasankar/mftool-java/dashboard?utm_source=github.com&utm_medium=referral&utm_content=ankitwasankar/mftool-java&utm_campaign=Badge_Coverage"><img src="https://app.codacy.com/project/badge/Coverage/0054db87ea0f426599c3a30b39291388" /></a>
<a href="https://www.codacy.com/gh/ankitwasankar/mftool-java/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ankitwasankar/mftool-java&amp;utm_campaign=Badge_Grade"><img src="https://app.codacy.com/project/badge/Grade/0054db87ea0f426599c3a30b39291388"/></a>
<a target="_blank" href="https://github.com/ankitwasankar/mftool-java/blob/master/license.md"><img src="https://camo.githubusercontent.com/8298ac0a88a52618cd97ba4cba6f34f63dd224a22031f283b0fec41a892c82cf/68747470733a2f2f696d672e736869656c64732e696f2f707970692f6c2f73656c656e69756d2d776972652e737667" /></a>
&nbsp <a target="_blank" href="https://www.linkedin.com/in/ankitwasankar/"><img height="20" src="https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" /></a>
</p>
<p align="center">
  This repository contains the <strong>MF TOOL - JAVA</strong> source code.
  MF TOOL - JAVA is a Java library developed to ease the process of working with Indian Mutual Funds. It's powerful, actively maintained and easy to use.
</p>

<p align="center">
<a href="#introduction">Introduction</a> &nbsp;&bull;&nbsp;
<a href="#installation">Installation</a> &nbsp;&bull;&nbsp;
<a href="#usage">Usage</a> &nbsp;&bull;&nbsp;
<a href="#documentation">Documentation</a> &nbsp;&bull;&nbsp;
<a href="#issue">Issue?</a>
</p>

# Introduction
This <b>mf-tool java</b> library provides simple APIs/functions/methods to work with Indian Mutual Funds. You can:

- Fetch a list of all mutual fund schemes.
- Fetch a list of matching mutual fund schemes based on provided keywords.
- Fetch historic or current NAV (Net Asset Value) for a fund.
- Fetch details for a fund and fund house.
- Integrate this with any Java project.

## Installation
##### Maven
```
<dependency>
  <groupId>com.webencyclop.core</groupId>
  <artifactId>mftool-java</artifactId>
  <version>1.0.4</version>
</dependency>
```
##### Graddle
```
implementation 'com.webencyclop.core:mftool-java:1.0.4'
```
For other dependency management tool, please visit
<a href="https://search.maven.org/artifact/com.webencyclop.core/mftool-java">https://search.maven.org/artifact/com.webencyclop.core/mftool-java</a>


## Usage
Sample code that shows how to use the library:<br/>
```
MFTool tool = new MFTool();
tool.matchingScheme("Axis");   //-- get a list of all schemes with Axis in its name
tool.getCurrentNav("120503");  //-- get current nav
```
The other available methods are described in the next section.

## Documentation
Multiple methods provide ways to work with mutual funds and related data. Those are listed below in detail.

### 1. How to initialize an MFTool object
```
MFTool tool = new MFTool();
```
This will create the object for you, but it's recommended that you create this object as a <b>singleton</b> object.
The object uses a caching mechanism, which under-the-hood caches the values of historic nav and other static information to improve the performance. 
<br/>If you are using the Spring project, you can create the bean in ``@Configuration`` configuration class.
```
@Configuration
public class MFToolConfig{
    @Bean
    public MFTool initializeMfTool() {
        MFTool tool = new MFTool();
        return tool;
    }
}
```
You can use MFTool in other services using ``@Inject`` or ``@autowired`` annotation.
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public void getCurrentNav(String scheme) {
        BigDecimal nav = tool.getCurrentNav(scheme);
    }
}
```

### 2. How to fetch a list of all mutual fund schemes
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public List<SchemeNameCodePair> fetchListOfAllMutualFundSchemes() {
        List<SchemeNameCodePair> list = tool.allSchemes();
    }
}
```

### 3. How to fetch a list of all schemes matching a keyword
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public List<SchemeNameCodePair> getCurrentNav(String schemeCode) {
        List<SchemeNameCodePair> list = tool.matchingScheme("Axis"); 
        // This will fetch MF schemes that have "Axis" in the name.
    }
}
```

### 4. Current NAV for the mutual fund scheme
An example schemeCode is 120503 (_Axis Long Term Equity Fund - Direct Plan - Growth Option_).<br/>
When we fetch a list of mutual funds, we get the scheme-name, and its corresponding schemeCode.<br/>
<b>A scheme code uniquely identifies the mutual fund scheme.</b>
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public List<SchemeNameCodePair> fetchListSchemes(String schemeCode) {
        BigDecimal nav = tool.getCurrentNav(schemeCode);
    }
}
```

### 5. NAV on specific date for the scheme
LocalDate is used to define the date. For example:<br/>
``LocalDate date = LocalDate.parse("2021-07-13");``
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public List<SchemeNameCodePair> getNavOnDate(String schemeCode, LocalDate date) {
        BigDecimal nav = tool.getNavFor("120503", date);
    }
}
```

### 6. List of historic NAV for the scheme
This method provides a list of all the NAVs for the given scheme.
```
@Service
public class MyService {
    
    @Autowired
    private MFTool tool;

    public List<SchemeNameCodePair> getNavOnDate(String schemeCode) {
        List<Data> list = tool.historicNavForScheme(schemeCode);
    }
}
```


## Issue
This repository is maintained actively, so if you face any issue please <a href="https://github.com/ankitwasankar/mftool-java/issues/new">raise an issue</a>.

<h4>Liked the work ?</h4>
Give the repository a star :-)
