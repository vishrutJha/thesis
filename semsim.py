from SPARQLWrapper import SPARQLWrapper,JSON
import cyttron
from pygraph.classes.digraph import digraph
from pygraph.readwrite.dot import write
import sqlite3
from gensim import corpora, models, similarities
from nltk.corpus import stopwords, wordnet
from nltk import word_tokenize, pos_tag, WordPunctTokenizer
import os

cyttron.fillDict()
dicto = cyttron.labelDict
dicto[u'http://purl.obolibrary.org/obo/IAO_0000115']='Anatomical entity that has no mass'
context = []
queue = []
visited = []
path = []
iup = 0
#contextURI = 'file://mpath.owl'
conn = sqlite3.connect('db/paths.db')
conn2 = sqlite3.connect('db/nodes.db')
endpoint = 'http://localhost:8080/openrdf-sesame/repositories/cyttron'
LCS = []
#contextURI = 'http://dbpedia.org'
#endpoint = 'http://dbpedia.org/sparql'
#conn = sqlite3.connect('db/dbp.db')
#conn2 = sqlite3.connect('db/dbpnodes.db')
done = False

dicto[u'http://www.w3.org/2000/01/rdf-schema#subClassOf'] = 'subclass of'
dicto[u'http://purl.org/obo/owl/obo#goslim_pir'] = "#goslim_pir"
dicto[u'http://www.geneontology.org/formats/oboInOwl#inSubset'] = "in subset"

URIx = 'http://purl.obolibrary.org/obo/MPATH_12'
URIy = 'http://purl.obolibrary.org/obo/MPATH_10'

log = open('pathfinderlog.txt','w')

class MyQUEUE:	
    def __init__(self):
        self.holder = []
    def enqueue(self,val):
        self.holder.append(val)
    def dequeue(self):
        val = None
        try:
            val = self.holder[0]
            if len(self.holder) == 1:
                self.holder = []
            else:
                self.holder = self.holder[1:]	
        except:
            pass	
        return val		
    def IsEmpty(self):
        result = False
        if len(self.holder) == 0:
            result = True
        return result

def SemSim(URI1,URI2):
    global queue,visited,done,log,path
    q = MyQUEUE()
    
    # Sort list so node1-node2 == node2-node1
    lijstje=[URI1,URI2]
    URI1 = sorted(lijstje)[0]
    URI2 = sorted(lijstje)[1]

    log = open('pathfinderlog.txt','a')                            
    log.write('"node1";"' + str(URI1) + '"\n')
    log.write('"node2";"' + str(URI2) + '"\n')
    log.close()

    # Check if URI-path is already in db
    c = conn.cursor()
    c.execute('SELECT * FROM thesis WHERE node1=? AND node2=?',(URI1,URI2))

    # If it is, return the data
    if len(c.fetchall()) > 0:
        print "Initial URI Path already exists!",URI1.rsplit('/')[-1],"-",URI2.rsplit('/')[-1]
        c.execute('SELECT * FROM thesis WHERE node1=? AND node2=?',(URI1,URI2))
        result = c.fetchall()
        c.close()
        URI1 = result[0][0]
        URI2 = result[0][1]
        pathlength = result[0][2]
        path = eval(result[0][3])
        print "pathlength:",pathlength
        print "path:",path
        log = open('pathfinderlog.txt','a')
        log.write('"pathlength";"' + str(pathlength) + '"\n')
        log.close()
        done = True

    # If it's not, start BFS algorithm
    else:
        done = False
        queue=[]
        visited=[]
        q.enqueue([URI1])
        while q.IsEmpty() == False:
            curr_path = q.dequeue()
            queue.append(curr_path)
            for i in range(len(curr_path)):
                if len(curr_path) == 1 and type(curr_path) is not list:
                    # If current path is a single URI, means 1st cycle
                    node = curr_path[0]
                    print "Start node:",node
                    visited.append(node)
                    getNodes(node)
                    q.enqueue(context)

                if len(curr_path) > 1:
                    node1 = curr_path[i][0]
                    node2 = curr_path[i][2]
                    edgeLabel = curr_path[i][1]
                    # No target node found: add node to visited list and fetch neighbours (if its not visited + not one of the ignored nodes)
                    if node1 not in visited and 'http://www.w3.org/2002/07/owl#Class' not in node1 and 'http://www.geneontology.org/formats/oboInOwl#ObsoleteClass' not in node1:
                        node = node1
                        visited.append(node)
                        getNodes(node)
                        checkNodes(context,URI1,URI2)
                        if len(path) > 0:
                            return "Done"
                        else:
                            # print "No match found..."                            
                            q.enqueue(context)                        
                    elif node2 not in visited and 'http://www.w3.org/2002/07/owl#Class' not in node2 and 'http://www.geneontology.org/formats/oboInOwl#ObsoleteClass' not in node2:
                        node = node2
                        visited.append(node)
                        getNodes(node)
                        checkNodes(context,URI1,URI2)
                        if len(path) > 0:
                            print path
                            return "Done"
                        else:
                            # print "No match found..."
                            q.enqueue(context)

def checkNodes(context,URI1,URI2):
    global path,queue
    done = False
    # print "checking neighbours..."    
    for i in range(len(context)):
        node1 = context[i][0]
        node2 = context[i][2]
        # print "node1:",node1.rsplit('/')[-1],"node2:",node2.rsplit('/')[-1],"\t",URI2.rsplit('/')[-1]
        if node1 == URI2 or node2 == URI2:
            queue.append(context)
            done = True
            print "URI1:",URI1
            print "URI2:",URI2
            showPath(queue,URI1,URI2)
        else:
            done = False
        if done == True:
            string = "Found a link! Stored in path. Length:",len(path),"| Visited:",len(visited),"nodes."
            log = open('pathfinderlog.txt','a')                            
            log.write('"pathlength";"' + str(len(path)) + '"\n')
            log.close()
            print string
            print 'Wrote path to log-file'
            c = conn.cursor()
            c.execute('SELECT * FROM thesis WHERE node1=? AND node2=?',(URI1,URI2))
            if len(c.fetchall()) > 0:
                print "BEST VER Path already exists!"
            else:
                print "BEST VER Inserting path!"
                c.execute('insert into thesis values (?,?,?,?)',(URI1,URI2,len(path),str(path)))
                conn.commit()
            c.close()
            findFlips(path,URI1,URI2)
            return path
    return path

def createGraph(list_of_nodes):
    global path,dicto,pathList,G

    # Default settings
    G = digraph()
    G.add_node("graph",[("layout","circo")])
    G.add_node("node",[("style","filled"),("fontname","Arial"),("fontsize","13"),('fontcolor','white'),('shape','circle')])
    G.add_node("edge",[("fontname","Arial"),("fontsize","10"),('fontcolor','azure4')])

    # Double for-loop to go through all nodes/connections
    for i in range(len(list_of_nodes)):
        currentURI = list_of_nodes[i]        
        for j in range(i+1,len(list_of_nodes)):
            otherURI = list_of_nodes[j]
            SemSim(otherURI,currentURI)

            # plot BFS result
            for i in range(len(path)):
                nodeLeft = path[i][0]
                edgeLabel = path[i][1]
                nodeRight = path[i][2]

            # plot parent1
            findParents([[currentURI]])
            log = open('pathfinderlog.txt','a')                            
            log.write('"node1 depth: ' + str(pathList[0][0]) + '";"' + str(len(pathList)) + '"\n')
            log.close()
            for i in range(1,len(pathList)):
                prevNode = pathList[i-1][0]
                node = pathList[i][0]

            # plot parent2
            findParents([[otherURI]])
            log = open('pathfinderlog.txt','a')                            
            log.write('"node2 depth: ' + str(pathList[0][0]) + '";"' + str(len(pathList)) + '"\n')
            log.close()        
            for i in range(1,len(pathList)):
                prevNode = pathList[i-1][0]
                node = pathList[i][0]
                    
            findLCS(currentURI,otherURI)
            
            pathGraph(path) 

    # write path to DOT
    dot = write(G)
    f = open('path.gv','w')
    f.write(dot)
    f.close()    

def drawGraph(nodes):
    global path,dicto,pathList,G,LCS,contextURI

    # Default settings
    G = digraph()
    G.add_node("node",[("fontname","Arial"),("fontsize","8"),('fontcolor','black'),('shape','circle'),('fixedsize','true'),('penwidth','5')])
    G.add_node("edge",[("fontname","Arial"),("fontsize","7"),('fontcolor','azure4'),('penwidth','3'),("color","grey")])

    def drawStart(nodeList,number):
        global path,dicto,pathList,G,LCS        
        # Double for-loop to go through all nodes. Draw start nodes
        for i in range(len(nodeList)):
            currentURI = nodeList[i][3]
            currentNS = nodeList[i][2]
            for j in range(i+1,len(nodeList)):
                if nodeList[j][2] == 'ehda':
                    color = 'seagreen2'
                if nodeList[j][2] == 'nci':
                    color = 'lightsalmon'
                if nodeList[j][2] == 'ncbi':
                    color = 'pink'                
                if nodeList[j][2] == 'doid':
                    color = 'salmon'
                if nodeList[j][2] == 'go':
                    color = 'orange'
                if nodeList[j][2] == 'mpath':
                    color = 'red'                    
                if nodeList[j][2] == currentNS:
                    node1 = str(nodeList[j][1])
                    node2 = str(nodeList[i][1])
                    if G.has_node(node1) is False:
                        if number == 1:
                            size = nodeList[j][0]
                            G.add_node(node1,[("color",(color)),("style","filled"),('width',size),('height',size)])
                            print "\tdrawStart - added to Graph:",node1
                        else:
                            size = nodeList[j][0]
                            G.add_node(node1,[("color",(color)),('width',size),('height',size)])
                            print "\tdrawStart - added to Graph:",node1
                    if G.has_node(node2) is False:
                        if number == 1:
                            size = nodeList[i][0]
                            G.add_node(node2,[("color",(color)),("style","filled"),('width',size),('height',size)])
                            print "\tdrawStart - added to Graph:",node2
                        else:
                            size = nodeList[i][0]                            
                            G.add_node(node2,[("color",(color)),('width',size),('height',size)])
                            print "\tdrawStart - added to Graph:",node2

    def drawLCS(nodeList):
        global path,dicto,pathList,G,LCS        
        # Second double for-loop to go through all the LCSes. Draw LCS.
        for i in range(len(nodeList)):
            currentURI = nodeList[i][3]
            for j in range(i+1,len(nodeList)):
                otherURI = nodeList[j][3]
                findLCS(currentURI,otherURI)
                if LCS[0][0] != 0:
                    LCSnode = str(dicto[LCS[0][0]])
                    if G.has_node(LCSnode) is False:
                        G.add_node(LCSnode,[("color","peru"),('width','0.4'),('height','0.4')])
                        print "\tdrawLCS - added to Graph:",LCSnode

    def drawParents(nodeList):
        global path,dicto,pathList,G,LCS    
        # Third double for-loop to go through all the parents. Draw parents.
        for i in range(len(nodeList)):
            currentURI = nodeList[i][3]
            findParents([[currentURI]])
            for i in range(1,len(pathList)):
                for j in range(len(pathList[i])):
                    print j,
                    print pathList[i][j]
                    prevNode = str(dicto[pathList[i][j][0]])
                    node = str(dicto[pathList[i][j][1]])
                    if G.has_node(prevNode) is False:
                        G.add_node(prevNode,[("color","grey"),("width","0.3"),("height","0.3")])
                        print "\tdrawParents - added to Graph:",prevNode
                    if G.has_node(node) is False:
                        G.add_node(node,[("color","grey"),("width","0.3"),("height","0.3")])
                        print "\tdrawParents - added to Graph:",node
                    if G.has_edge((prevNode,node)) is False:
                        G.add_edge((prevNode,node),label="subClassOf")

    def drawBFS(nodeList):
        global contextURI,path
        nciNodes=[]
        doidNodes=[]
        ncbiNodes=[]
        goNodes=[]
        allNodes = nodeList[0] + nodeList[1]
        for i in range(len(allNodes)):
            if allNodes[i][2] == 'nci':
                nciNodes.append(allNodes[i])
            if allNodes[i][2] == 'doid':
                doidNodes.append(allNodes[i])
            if allNodes[i][2] == 'ncbi':
                ncbiNodes.append(allNodes[i])
            if allNodes[i][2] == 'go':
                goNodes.append(allNodes[i])   
                
        print len(nciNodes),"nci nodes"
        print len(doidNodes),'doid nodes'
        print len(ncbiNodes),'ncbi nodes'
        print len(goNodes),'go nodes'
        allNodes = [doidNodes,goNodes]

        for i in range(len(allNodes)):
            current = allNodes[i]
            if len(current) > 0:
                for j in range(len(current)):
                    NS = current[j][2]
                    if NS == 'ehda':
                        contextURI = "file://ehda.owl"
                        color = 'seagreen2'
                    if NS == 'doid':
                        contextURI = "file://doid.owl"
                        color = 'salmon'
                    if NS == 'nci':
                        contextURI = "file://nci.owl"
                        color = 'lightsalmon'
                    if NS == 'ncbi':
                        contextURI = "file://ncbi.owl"
                        color = 'pink'
                    if NS == 'go':
                        contextURI = "file://go.owl"
                        color = 'orange'
                    if NS == 'mpath':
                        contextURI = "file://go.owl"
                        color = 'red'                        
                    currentURI = current[j][3]
                    for k in range(j+1,len(current)):
                        otherURI = current[k][3]
                        if current[j][2] == current[k][2]:
                            path=[]
                            SemSim(otherURI,currentURI)
                            for i in range(len(path)):
                                node1=str(dicto[path[i][0]])
                                edge=str(dicto[path[i][1]])
                                node2=str(dicto[path[i][2]])
                                if G.has_node(node1) is False:
                                    G.add_node(node1,attrs=[('color', 'grey')])
                                if G.has_node(node2) is False:
                                    G.add_node(node2,attrs=[('color', 'grey')])
                                if G.has_edge((node1,node2)) is False:                    
                                    G.add_edge((node1,node2),label=str(edge).rsplit('/')[-1],attrs=[('color', color)])
                                    
    words = nodes[0]
    nonLit = nodes[1]

    drawStart(words,1)
    drawStart(nonLit,0)
    drawBFS(nodes)

    drawLCS(words)
    drawLCS(nonLit)    
    drawParents(words)
    drawParents(nonLit)

    # write path to DOT
    dot = write(G)
    f = open('path.gv','w')
    f.write(dot)
    f.close()
    os.system("gv\\bin\\dot.exe -Tpng -ograph.png path.gv")
    print "Created graph.png"

def relabel(text):
    # from URI to label
    global dicto
    for i, j in dicto.iteritems():
        text = text.replace(i, j)
    return text

def showPath(list,start,target):
    global path
    path = []
    for x in range(len(list),0,-1):
        if x-1 > 1:
            hop = list[x-1]
            for i in range(len(hop)):
                leftNode = hop[i][0]
                rightNode = hop[i][2]
                if leftNode == target:
                    path.append(hop[i])
                    target = rightNode
                    break
                if rightNode == target:
                    path.append(hop[i])
                    target = leftNode
                    break
        if x-1 == 1:
            hop = list[x-1]
            for i in range(len(hop)):
                leftNode = hop[i][0]
                rightNode = hop[i][2]
                if leftNode == start and rightNode == target:
                    path.append(hop[i])
                    return path                    
                if rightNode == start and leftNode == target:
                    path.append(hop[i])
                    return path

def findFlips(path,start,target):
    flips = ""
    count=0
    for i in range(0,len(path)):
        prevLeft = path[i-1][0]
        prevRight = path[i-1][2]
        
        left = path[i][0]
        right = path[i][2]
        print left,right

        if left == prevRight:
            flips += "U"
        if right == prevRight:
            flips += "D"
        if right == prevLeft:
            flips += "D"
    print flips
    for i in range(1,len(flips)):
        prevLetter = flips[i-1]
        letter = flips[i]
        if letter == prevLetter:
            count += 0
        else:
            count += 1
    log = open('pathfinderlog.txt','a')                            
    log.write('"directionflips:";"' + str(count) + '"\n')
    log.close()
    return count

def getNodes(URI):
    global context,contextURI
    context=[]
    c = conn2.cursor()
    c.execute('SELECT * FROM nodes WHERE URI=?', (URI,))
    result = c.fetchall()
    c.close()    
    if len(result) > 0:
        #print "Node in DB"
        context = eval(result[0][1])
        c.close()
    else:
        sparql = SPARQLWrapper(endpoint)
        print URI.rsplit('/')[-1],"has",
        
        #Direct
        querystring=""" SELECT DISTINCT ?p ?s FROM <""" + str(contextURI) + """> WHERE {
            { <""" + str(URI) + """> ?p ?s . FILTER ( isURI(?s )) . }
            }"""
        sparql.setReturnFormat(JSON)
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            if 'http://www.w3.org/' not in x['s']['value']:            
                context.append([URI,x["p"]["value"],x["s"]["value"]])

        querystring=""" SELECT DISTINCT ?o ?p FROM <""" + str(contextURI) + """> WHERE {
        { ?o ?p <""" + str(URI) + """> . FILTER (isURI(?o )) . }
        }"""
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            if 'http://www.w3.org/' not in x['o']['value']:            
                context.append([x["o"]["value"],x["p"]["value"],URI])
                
        print len(context),"neighbours (to db)"
        c = conn2.cursor()
        t = (URI,str(context))
        c.execute('insert into nodes values (?,?)', t)
        conn2.commit()
        c.close()
    return context

#======================================================#
# 'shared parents' stuff                               #
#======================================================#

def findLCS(URI1,URI2):
    global LCS
    LCS = []
    LCS = [[findCommonParents(URI1,URI2)]]
    if LCS[0][0] != 0:
        findParents(LCS)
        log = open('pathfinderlog.txt','a')                            
        log.write('"LCS depth: ' + str(pathList[0][0]) + '";"' + str(len(pathList)) + '"\n')
        log.close()
    else:
        print "No LCS"

def findParents(URI):
    # Returns a pathList which includes all parents per hop
    global iup, pathList,endpoint
    list_out=[]
    iup += 1
    if iup == 1:
        sparql = SPARQLWrapper(endpoint)
        sparql.addCustomParameter("infer","false")
        sparql.setReturnFormat(JSON)        
        querystring = 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?super WHERE { <' + URI[iup-1][0] + '> rdfs:subClassOf ?super . FILTER isURI(?super) }'
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            list_out.append((URI[iup-1][0],x["super"]["value"]))
    else:
        for i in range(len(URI[iup-1])):
            sparql = SPARQLWrapper(endpoint)
            sparql.addCustomParameter("infer","false")
            sparql.setReturnFormat(JSON)
            querystring = 'PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?super WHERE { <' + URI[iup-1][i][1] + '> rdfs:subClassOf ?super . FILTER isURI(?super) }'
            sparql.setQuery(querystring)
            results = sparql.query().convert()
            for x in results["results"]["bindings"]:
                list_out.append((URI[iup-1][i][1],x["super"]["value"]))
                
    if len(list_out) > 0:
        URI.append(list_out)
        findParents(URI)
    else:
        iup=0
        pathList = URI
        return pathList

def findCommonParents(URI1,URI2):
    global done,result1,result2,pathList,parent1,parent2
    done = False
    # Input URI strings, output common Parent
    # print ""
    URI1 = [[URI1]]
    URI2 = [[URI2]]
    iup = 0

    # First pathList generation
    findParents(URI1)
    #print "[findCommonP]\t","1st URI processed\n"
    result1 = pathList
    #print result1
    
    # Flush results for 2nd
    pathList = []

    # Second pathList generation
    findParents(URI2)
    #print "[findCommonP]\t","2nd URI processed\n"
    result2 = pathList
    #print result2

    for i in range(1,len(result1)):
        for j in range(1,len(result2)):
            for i2 in range(len(result1[i])):
                for j2 in range(len(result2[j])):
                    if set(result1[i][i2][1]) == set(result2[j][j2][1]):
                        #print "[findCommonP]\t","CommonParent found!"
                        done = True
                        #print "[findCommonP]\t","Result1[" + str(i) + "][" + str(i2) +"]",
                        #print "matches with result2[" +str(j) + "][" + str(j2) + "]"
                        #print "[findCommonP]\t",result1[i][i2]
                        parent1 = result1
                        parent2 = result2
                        if done == True:
                            return result1[i][i2][1]
    return 0

def compare(URI1,URI2):
    URI1context = getContext(URI1)
    URI2context = getContext(URI2)
    cyttron.compareDoc(str(URI1context[0]),str(URI2context[0]))
    cyttron.compareDoc(str(URI1context[0]),str(URI2context[1]))
    cyttron.compareDoc(str(URI1context[1]),str(URI2context[0]))
    cyttron.compareDoc(str(URI1context[1]),str(URI2context[1]))    

#======================================================#
# Textual comparison                                   #
#======================================================#
def getContext(node1):
    context1=[]
    neighboursOut=[]
    neighboursIn=[]
    sparql = SPARQLWrapper(endpoint)
    print endpoint

    # Get own out literals
    querystring="SELECT DISTINCT ?s WHERE { <" + str(node1) + "> ?p ?s . FILTER (isLiteral(?s ))  }"
    print querystring
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        if 'http://www.w3.org/2002/07/owl#Class' not in x["s"]["value"]:
            context1.append(x["s"]["value"])
            print "Own OUT literals:",x["s"]["value"]

    # Get own out bnode-literals
    querystring="PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?desc WHERE { <" + str(node1) + "> ?p ?s . ?s ?x ?desc . FILTER (isBlank(?s )) . FILTER (isLiteral(?desc)) }"
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        if 'http://www.w3.org/2002/07/owl#Class' not in x["desc"]["value"]:
            context1.append(x["desc"]["value"])
            print "Own OUT bnode-literals:",x["desc"]["value"]

    # Get own in literals
    querystring="SELECT DISTINCT ?o WHERE { ?o ?p <" + str(node1) + "> . FILTER (isLiteral(?o )) }"
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        context1.append(x["o"]["value"])
        print "Own IN literals",x["o"]["value"]

    # Get own in bnode-literals
    querystring="PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?desc WHERE { ?o ?p <" + str(node1) + "> . ?o ?x ?desc . FILTER (isBlank(?o )) . FILTER (isLiteral(?desc)) }"
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        context1.append(x["desc"]["value"])
        print "Own IN literals:",x["desc"]["value"]
    direct = context1
    print "Final direct:",direct
    context1=[]

    # Get all out neighbour URI's
    querystring="SELECT DISTINCT ?s WHERE { <" + str(node1) + "> ?p ?s . FILTER (isURI(?s ))  }"
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        if 'http://www.w3.org/2002/07/owl#Class' not in x["s"]["value"]:
            neighboursOut.append(x["s"]["value"])
    print "Neighbour OUT nodes:",neighboursOut

    # Get all in neighbour URI's
    querystring="SELECT DISTINCT ?o WHERE { ?o ?p <" + str(node1) + "> . FILTER (isURI(?o )) }"
    sparql.setReturnFormat(JSON)
    sparql.addCustomParameter("infer","false")
    sparql.setQuery(querystring)
    results = sparql.query().convert()
    for x in results["results"]["bindings"]:
        if 'http://www.w3.org/2002/07/owl#Class' not in x["o"]["value"]:
            neighboursIn.append(x["o"]["value"])
    print "Neighbours IN:",neighboursIn

    # Get literal + bnode-literals for OUT neighbours
    for i in range(len(neighboursOut)):
        # Get all neighbour literals
        querystring="SELECT DISTINCT ?s WHERE { <" + str(neighboursOut[i]) + "> ?p ?s . FILTER (isLiteral(?s ))  }"
        sparql.setReturnFormat(JSON)
        sparql.addCustomParameter("infer","false")
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            context1.append(x["s"]["value"])

        # Get all neighbour bnode-literals
        querystring="PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?desc WHERE { <" + str(neighboursOut[i]) + "> ?p ?s . ?s ?x ?desc . FILTER (isBlank(?s )) . FILTER (isLiteral(?desc)) }"
        sparql.setReturnFormat(JSON)
        sparql.addCustomParameter("infer","false")
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            context1.append(x["desc"]["value"])

    # Get literal + bnode-literals for IN neighbours
    for i in range(len(neighboursIn)):
        querystring="SELECT DISTINCT ?o WHERE { ?o ?p <" + str(neighboursIn[i]) + "> . FILTER (isLiteral(?o )) }"
        sparql.setReturnFormat(JSON)
        sparql.addCustomParameter("infer","false")
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            context1.append(x["o"]["value"])

        querystring="PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> SELECT DISTINCT ?desc WHERE { ?o ?p <" + str(neighboursIn[i]) + "> . ?o ?x ?desc . FILTER (isBlank(?o )) . FILTER (isLiteral(?desc)) }"
        sparql.setReturnFormat(JSON)
        sparql.addCustomParameter("infer","false")
        sparql.setQuery(querystring)
        results = sparql.query().convert()
        for x in results["results"]["bindings"]:
            context1.append(x["desc"]["value"])
    neighbours = context1
    print "Direct:",direct
    print "Neighbours:",neighbours
    final = [direct,neighbours]
    print "\nFinal:",final
    return final

def pathGraph(path):
    global dicto,pathList,G,parent1,parent2

    # Add start nodes, add LCS, draw path in yellow
    startNode1=str(dicto[parent1[0][0]])
    startNode2=str(dicto[parent2[0][0]])
    LCS=str(dicto[pathList[0][0]])
    if G.has_node(startNode1) is False:
        G.add_node(startNode1,attrs=[('color', 'peru'),('size','2')])
    if G.has_node(startNode2) is False:
        G.add_node(startNode2,attrs=[('color', 'peru'),('size','2')])
    if G.has_node(LCS) is False:       
        G.add_node(LCS,attrs=[('color', 'seagreen2'),('size','2')])
    
    for i in range(len(path)):
        node1=str(dicto[path[i][0]])
        edge=str(dicto[path[i][1]])
        node2=str(dicto[path[i][2]])
        if G.has_node(node1) is False:
            G.add_node(node1,attrs=[('color', 'orange1')])
        if G.has_node(node2) is False:
            G.add_node(node2,attrs=[('color', 'orange1')])
        if G.has_edge((node1,node2)) is False:                    
            G.add_edge((node1,node2),label=str(edge).rsplit('/')[-1])

    for i in range(1,len(parent1)):
        prevNode = str(dicto[parent1[i-1][0]])
        node = str(dicto[parent1[i][0]])
        if G.has_node(prevNode) is False:
            G.add_node(prevNode,attrs=[('color', 'lightsalmon')])
        if G.has_node(node) is False:
            G.add_node(node,attrs=[('color', 'lightsalmon')])
        if G.has_edge((prevNode,node)) is False:
            G.add_edge((prevNode,node),label="subClassOf")

    for i in range(1,len(parent2)):
        prevNode = str(dicto[parent2[i-1][0]])
        node = str(dicto[parent2[i][0]])
        if G.has_node(prevNode) is False:
            G.add_node(prevNode,attrs=[('color', 'lightsalmon')])
        if G.has_node(node) is False:
            G.add_node(node,attrs=[('color', 'lightsalmon')])
        if G.has_edge((prevNode,node)) is False:
            G.add_edge((prevNode,node),label="subClassOf")
